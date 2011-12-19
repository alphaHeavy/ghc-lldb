import lldb
import ghc_map
import re

# (lldb) command script import '/Source/ghc-lldb/ghc.py'

class SyntheticClosureProvider(object):
    def __init__(self, valobj, dict):
        if valobj.AddressOf() == None:
            raise "AddressOf() == None"

        self.valobj = valobj
        self.update()

    def num_children(self):
        return self.closure.num_children() + 1

    def get_child_index(self, name):
        if name == 'info':
            return 0
        else:
            return self.closure.get_child_index(name) + 1

    def get_child_at_index(self,index):
        if index == 0:
            return self.closure.info_table().info_table
        else:
            return self.closure.get_child_at_index(index - 1)

    def update(self):
        self.closure = Closure.get(lldb.debugger, self.valobj.AddressOf())

class SyntheticInfoTableProvider(object):
    def __init__(self, valobj, dict):
        if valobj.AddressOf() == None:
            raise "AddressOf() == None"

        self.valobj = valobj
        self.update()

    def num_children(self):
        return 2

    def get_child_index(self, name):
        if name == 'type':
            return 0
        elif name == 'description':
            return 1
        else:
            return -1

    def get_child_at_index(self,index):
        if index == 0:
            return self.type
        if index == 1:
            return self.description
        else:
            return None

    def update(self):
        self.type = self.valobj.GetChildMemberWithName('type')
        self.info = InfoTable.get(lldb.debugger, self.valobj.AddressOf())
        self.description = self.info.con_desc2()

class Closure(object):
    def __init__(self, debugger, obj):
        self.debugger = debugger
        self.obj = obj
        self.payload = []

    # def __str__(self):
    #   return str(self.info_table()) + ' ' + str(self.payload)

    # def __repr__(self):
        # return '<Closure info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

    def num_children(self):
        return len(self.payload)

    def get_child_index(self, name):
        try:
            return int(name.lstrip('[').rstrip(']'))
        except:
            return -1;

    def get_child_at_index(self,index):
        return self.payload[index]

    def reify(self):
        info = self.info_table().info_table
        ptrs = info.GetValueForExpressionPath('.layout.payload.ptrs').GetValueAsUnsigned()
        nptrs = info.GetValueForExpressionPath('.layout.payload.nptrs').GetValueAsUnsigned()

        # lldb does bounds checks on array subscripts, which doesn't work with GHC's closure types
        # so strip the StgClosure[1] type of the array size, leaving StgClosure* (which is not bounds checked)
        payload = self.obj.GetValueForExpressionPath('.payload[0]').AddressOf()

        closure_type = find_first_type(lldb.debugger, 'StgClosure')
        i = 0
        while i < ptrs:
            name = 'arg{0}'.format(i)
            payload_i = payload.CreateChildAtOffset(name, i*8, closure_type.GetPointerType()).Dereference()
            self.payload.append(Closure.cast(self.debugger, payload_i))
            i += 1

        long_type = self.obj.GetType().GetBasicType(lldb.eBasicTypeUnsignedLong)
        while i < ptrs+nptrs:
            name = 'arg{0}'.format(i)
            payload_i = payload.CreateChildAtOffset(name, i*8, long_type)
            self.payload.append(payload_i.Cast(long_type))
            i += 1

    @staticmethod
    def untag(debugger, obj):
        closure_type = find_first_type(debugger, 'StgClosure')
        # closure_type = obj.GetType().GetPointeeType()
        ptr = obj.GetValueAsUnsigned()
        if ptr & 0x7 == 0:
            return obj
        else:
            ptr = ptr & ~7
            return obj.CreateValueFromAddress(obj.GetName(), ptr, closure_type)

    def info_table(self):
        target = self.debugger.GetSelectedTarget()

        # lldb doesn't support negative subscripts, this would be cleaner as '.header.info[-1]'
        info_table = self.obj.GetValueForExpressionPath('.header.info')
        info_table_sym = target.ResolveSymbolContextForAddress(info_table.Dereference().GetAddress(), lldb.eSymbolContextSymbol).GetSymbol()

        # cast it back to the info table
        stg_info_table_type = find_first_type(self.debugger, 'StgInfoTable_')
        offset_info_table = info_table.CreateValueFromAddress(decode_z_str(info_table_sym.GetName()), info_table.GetValueAsUnsigned() - 16, stg_info_table_type)

        return InfoTable(self.debugger, offset_info_table)

    @staticmethod
    def type_name(tag):
        name = ghc_map.closure_name_map[tag]
        return ghc_map.closure_type_map[name]

    @staticmethod
    def cast(debugger, obj):
        try:
            info_table = InfoTable.get(debugger, obj)
            # find what the runtime closure type is by inspecting the infotable type
            closure_type = info_table.type()
            type_tag = closure_type.GetValueAsUnsigned()
            type_name = Closure.type_name(type_tag)
            target = debugger.GetSelectedTarget()
            return obj.Cast(find_first_type(debugger, type_name))

        except:
            return obj

    @staticmethod
    def get(debugger, obj):
        if obj == None:
            return None

        obj = Closure.untag(debugger, obj)
        if obj == None:
            return None

        self = Closure(debugger, obj)

        # find what the runtime closure type is by inspecting the infotable type
        info_table = self.info_table()
        closure_type = info_table.type()
        type_tag = closure_type.GetValueAsUnsigned()
        type_name = Closure.type_name(type_tag)

        target = debugger.GetSelectedTarget()
        closure_type = find_first_type(debugger, type_name)
        # propagate the constructor desciption or info table name to the closure
        ctor = closure_print_map[ghc_map.closure_name_map[type_tag]]
        closure = ctor(debugger, obj.CreateValueFromAddress(str(info_table), obj.GetLoadAddress(), closure_type))
        closure.reify()

        return closure

    @staticmethod
    def get_expression(expr):
        frame = lldb.thread.GetSelectedFrame()
        obj = frame.EvaluateExpression(expr)
        return Closure.get(lldb.debugger, obj)

class Constructor(Closure):
    def __init__(self, debugger, obj):
        super(Constructor, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<Constructor info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class Function(Closure):
    def __init__(self, debugger, obj):
        super(Function, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<Function info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class Thunk(Closure):
    def __init__(self, debugger, obj):
        super(Thunk, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<Thunk info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class Selector(Closure):
    def __init__(self, debugger, obj):
        super(Selector, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<Selector info_table:{0} selectee:{1}>'.format(self.info_table(), self.selectee)

    def reify(self):
        super(Selector, self).reify()
        self.selectee = Closure.get(self.debugger, self.obj.GetChildMemberWithName('selectee'))

class BCO(Closure):
    def __init__(self, debugger, obj):
        super(BCO, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<BCO info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class PAP(Closure):
    def __init__(self, debugger, obj):
        super(PAP, self).__init__(debugger, obj)

    def __foorepr__(self):
        return '<PAP info_table:{0} arity:{1} n_args:{2} fun:{3} payload:{4}>'.format(
            self.info_table(),
            self.arity.GetValue(),
            self.n_args.GetValue(),
            self.fun.GetValue(),
            self.payload)

    def reify(self):
        super(PAP, self).reify()
        self.arity = self.obj.GetChildMemberWithName('arity')
        self.n_args = self.obj.GetChildMemberWithName('n_args')
        self.fun = self.obj.GetChildMemberWithName('fun')

class AP(PAP):
    def __init__(self, debugger, obj):
        super(AP, self).__init__(debugger, obj)

    def __foorepr__(self):
        return '<AP info_table:{0} arity:{1} n_args:{2} fun:{3} payload:{4}>'.format(
            self.info_table(),
            self.arity.GetValue(),
            self.n_args.GetValue(),
            self.fun.GetValue(),
            self.payload)

class AP_STACK(Closure):
    def __init__(self, debugger, obj):
        super(AP_STACK, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<AP_STACK info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class Ind(Closure):
    def __init__(self, debugger, obj):
        super(Ind, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<Ind info_table:{0} indirectee:{1}>'.format(self.info_table(), self.indirectee.GetValue())

    def reify(self):
        super(Ind, self).reify()
        self.indirectee = self.obj.GetChildMemberWithName('indirectee')

class IndStatic(Closure):
    def __init__(self, debugger, obj):
        super(IndStatic, self).__init__(debugger, obj)

    def __foorepr__(self):
        return '<IndStatic info_table:{0} indirectee:{1} static_link:{2} saved_info:{3}>'.format(
            self.info_table(),
            self.indirectee.GetValue(),
            self.static_link.GetValue(),
            self.saved_info.GetValue())

    def reify(self):
        super(IndStatic, self).reify()
        self.indirectee = self.obj.GetChildMemberWithName('indirectee')
        self.static_link = self.obj.GetChildMemberWithName('static_link') # StgClosure
        self.saved_info = self.obj.GetChildMemberWithName('saved_info') # StgInfoTable

class RetSmall(Closure):
    def __init__(self, debugger, obj):
        super(RetSmall, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<RetSmall info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class RetBig(Closure):
    def __init__(self, debugger, obj):
        super(RetBig, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<RetBig info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class RetDyn(Closure):
    def __init__(self, debugger, obj):
        super(RetDyn, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<RetDyn info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class RetFun(Closure):
    def __init__(self, debugger, obj):
        super(RetFun, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<RetFun info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class UpdateFrame(Closure):
    def __init__(self, debugger, obj):
        super(UpdateFrame, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<UpdateFrame info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class CatchFrame(Closure):
    def __init__(self, debugger, obj):
        super(CatchFrame, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<CatchFrame info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class UnderflowFrame(Closure):
    def __init__(self, debugger, obj):
        super(UnderflowFrame, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<UnderflowFrame info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class StopFrame(Closure):
    def __init__(self, debugger, obj):
        super(StopFrame, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<StopFrame info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class BlockingQueue(Closure):
    def __init__(self, debugger, obj):
        super(BlockingQueue, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<BlockingQueue info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class BlackHole(Closure):
    def __init__(self, debugger, obj):
        super(BlackHole, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<BlackHole info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class MVar(Closure):
    def __init__(self, debugger, obj):
        super(MVar, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<MVar head:{0} tail:{1} value:{2}>'.format(self.head, self.tail, self.value)

    def reify(self):
        super(MVar, self).reify()
        self.head = self.obj.GetChildMemberWithName('head')
        self.tail = self.obj.GetChildMemberWithName('tail')
        self.value = Closure.get(self.debugger, self.obj.GetChildMemberWithName('value'))

class Array(Closure):
    def __init__(self, debugger, obj):
        super(Array, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<Array info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class MutableArray(Closure):
    def __init__(self, debugger, obj):
        super(MutableArray, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<MutableArray info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

    def reify(self):
        super(MutableArray, self).reify()
        self.ptrs = self.obj.GetChildMemberWithName('ptrs')

    def num_children(self):
        return 1

    def get_child_index(self, name):
        if name == 'ptrs':
            return 0
        else:
            return None

    def get_child_at_index(self, index):
        if index == 1:
            return self.ptrs
        else:
            return None

class IORef(Closure):
    def __init__(self, debugger, obj):
        super(IORef, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<IORef info_table:{0} var:{1}>'.format(self.info_table(), self.var)

    def reify(self):
        super(IORef, self).reify()
        self.var = Closure.get(self.debugger, self.obj.GetChildMemberWithName('var'))

class WeakRef(Closure):
    def __init__(self, debugger, obj):
        super(WeakRef, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<WeakRef info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class Primitive(Closure):
    def __init__(self, debugger, obj):
        super(Primitive, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<Primitive info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class MutablePrimitive(Closure):
    def __init__(self, debugger, obj):
        super(MutablePrimitive, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<MutablePrimitive info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class TSO(Closure):
    def __init__(self, debugger, obj):
        super(TSO, self).__init__(debugger, obj)
        pass

    def __foorepr__(self):
        stackobj_str = self.stackobj.GetValue()
        what_next_str = TSO.what_next_map[self.what_next.GetValueAsUnsigned()]
        why_blocked_str = TSO.why_blocked_map[self.why_blocked.GetValueAsUnsigned()]
        return '<TSO id:{0} stackobj:{1} what_next:{2} why_blocked:{3} flags:{4} saved_errno:{5} dirty:{6} block_info:{7} bq:{8}>'.format(
            self.id.GetValue(),
            stackobj_str,
            what_next_str,
            why_blocked_str,
            self.flags.GetValue(),
            self.saved_errno.GetValue(),
            bool(self.dirty.GetValueAsUnsigned()),
            self.block_info.GetValue(),
            self.bq)

    what_next_map = {0:  'NotBlocked'
                    ,1:  'BlockedOnMVar'
                    ,2:  'BlockedOnBlackHole'
                    ,3:  'BlockedOnRead'
                    ,4:  'BlockedOnWrite'
                    ,5:  'BlockedOnDelay'
                    ,6:  'BlockedOnSTM'
                    ,7:  'BlockedOnDoProc'
                    ,8:  'BlockedOnGA'
                    ,9:  'BlockedOnGA_NoSend'
                    ,10: 'BlockedOnCCall'
                    ,11: 'BlockedOnCCall_Interruptible'
                    ,12: 'BlockedOnMsgThrowTo'
                    ,13: 'ThreadMigrating'}

    why_blocked_map = {0: 'Unknown'
                      ,1: 'ThreadRunGHC'
                      ,2: 'ThreadInterpret'
                      ,3: 'ThreadKilled'
                      ,4: 'ThreadComplete'}

    def reify(self):
        super(TSO, self).reify()
        self.stackobj = self.obj.GetChildMemberWithName('stackobj')
        self.what_next = self.obj.GetChildMemberWithName('what_next')
        self.why_blocked = self.obj.GetChildMemberWithName('why_blocked')
        self.flags = self.obj.GetChildMemberWithName('flags')
        self.id = self.obj.GetChildMemberWithName('id')
        self.saved_errno = self.obj.GetChildMemberWithName('saved_errno')
        self.dirty = self.obj.GetChildMemberWithName('dirty')
        self.block_info = self.obj.GetChildMemberWithName('block_info')
        self.bq = Closure.get(self.debugger, self.obj.GetChildMemberWithName('bq'))

class Stack(Closure):
    def __init__(self, debugger, obj):
        super(Stack, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<Stack stack_size:{0} dirty:{1} sp:{2} stack:{3}>'.format(self.stack_size.GetValueAsUnsigned(), bool(self.dirty.GetValueAsUnsigned()), self.sp.GetValue(), self.stack.GetValue())

    def reify(self):
        super(Stack, self).reify()
        self.stack_size = self.obj.GetChildMemberWithName('stack_size')
        self.dirty = self.obj.GetChildMemberWithName('dirty')
        self.sp = self.obj.GetChildMemberWithName('sp')
        self.stack = self.obj.GetChildMemberWithName('stack')

class TRecChunk(Closure):
    def __init__(self, debugger, obj):
        super(TRecChunk, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<TRecChunk info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class AtomicallyFrame(Closure):
    def __init__(self, debugger, obj):
        super(AtomicallyFrame, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<AtomicallyFrame info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class CatchRetryFrame(Closure):
    def __init__(self, debugger, obj):
        super(CatchRetryFrame, self).__init__(debugger, obj)

    # def __repr__(self):
        # return '<CatchRetryFrame info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class CatchSTMFrame(Closure):
    def __init__(self, debugger, obj):
        super(CatchSTMFrame, self).__init__(debugger, obj)

    def __repr__(self):
        return '<CatchSTMFrame info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

class InfoTable(object):
    def __init__(self, debugger, info_table):
        self.debugger = debugger
        self.info_table = info_table

    # def __str__(self):
    #    return self.con_desc() or self.info_table.GetName()

    # def __repr__(self):
        # name = self.con_desc() or self.info_table.GetName()
        # return '<InfoTable name:{0} entry:{1}>'.format(name, self.entry_symbol().GetName())

    def con_desc2(self):
        target = self.debugger.GetSelectedTarget()
        stg_con_info_table_type = find_first_type(self.debugger, 'StgConInfoTable_')
        # stg_con_info_table_type = target.FindFirstType('StgConInfoTable_') # waiting on bug 11574
        con_info = self.info_table.Cast(stg_con_info_table_type)
        con_info_ptr = con_info.AddressOf()
        char_type = self.info_table.GetType().GetBasicType(lldb.eBasicTypeChar)
        base = con_info_ptr.GetValueForExpressionPath('[1]')
        offset = con_info_ptr.GetValueForExpressionPath('[1].con_desc').GetValueAsUnsigned()
        return base.CreateChildAtOffset('description', offset, char_type).AddressOf()

    def con_desc(self):
        target = self.debugger.GetSelectedTarget()
        stg_con_info_table_type = find_first_type(self.debugger, 'StgConInfoTable_')
        # stg_con_info_table_type = target.FindFirstType('StgConInfoTable_') # waiting on bug 11574
        con_info = self.info_table.Cast(stg_con_info_table_type)
        con_info_ptr = con_info.AddressOf()
        char_type = self.info_table.GetType().GetBasicType(lldb.eBasicTypeChar)
        base = con_info_ptr.GetValueForExpressionPath('[1]')
        offset = con_info_ptr.GetValueForExpressionPath('[1].con_desc').GetValueAsUnsigned()
        summary = base.CreateValueFromAddress('con_desc', base.GetLoadAddress()+offset, char_type).AddressOf().GetSummary()
        return decode_z_str(summary.strip('"')) if summary else None

    def type(self):
        return self.info_table.GetChildMemberWithName('type')

    def entry_symbol(self):
        entry = self.info_table.AddressOf().GetValueForExpressionPath('[1]')
        target = self.debugger.GetSelectedTarget()
        return target.ResolveSymbolContextForAddress(entry.GetAddress(), lldb.eSymbolContextSymbol).GetSymbol()

    @staticmethod
    def get(debugger, obj):
        return InfoTable(debugger, obj)

def find_first_type(debugger, type_name):
    target = debugger.GetSelectedTarget()
    return target.FindTypes(type_name).GetTypeAtIndex(0)

def print_std_obj_header(obj, tag):
    # print tag + '('
    print obj.GetValueForExpressionPath('.header.info')
    print obj.GetValueForExpressionPath('.header.prof.ccs->cc->label')

def print_std_obj_payload(debugger, obj):
    target = debugger.GetSelectedTarget()
    info = ghc.get_info_table_from_closure(obj)
    ptrs = info.GetValueForExpressionPath('.layout.payload.ptrs').GetValueAsUnsigned()
    nptrs = info.GetValueForExpressionPath('.layout.payload.nptrs').GetValueAsUnsigned()

    # lldb does bounds checks on array subscripts, which doesn't work with GHC's closure types
    # so strip the StgClosure[1] type of the array size, leaving StgClosure* (which is not bounds checked)
    payload = obj.GetValueForExpressionPath('.payload[0]').AddressOf()

    i = 0
    while i < ptrs:
        payload_i = payload.GetValueForExpressionPath('[' + str(i) + ']')
        print str(i) + ': ' + payload_i.GetValue() + ' = ' + get_object_description(untag_closure(payload_i))
        i += 1

    j = 0
    while j < nptrs:
        payload_j = payload.GetValueForExpressionPath('[' + str(i+j) + ']')
        print str(i+j) + ': ' + payload_j.GetValue() + '#d'
        j += 1

def print_obj_dbg(debugger, args, result, dict):
    frame = lldb.thread.GetSelectedFrame()
    obj = frame.EvaluateExpression(args) # frame.FindValue(args, lldb.eValueTypeRegister)
    obj = Closure.get(debugger, obj)
    print obj
    # print_std_obj_payload(obj)
    return None

def print_base_reg(debuger, args, result, dict):
    frame = lldb.thread.GetSelectedFrame()
    print frame.EvaluateExpression('*((StgRegTable_*)$r13)')

def print_current_tso(debugger, args, result, dict):
    frame = lldb.thread.GetSelectedFrame()
    print frame.EvaluateExpression('*((StgRegTable_*)$r13)->rCurrentTSO')

z_decoder = {'ZL': '('
            ,'ZR': ')' 
            ,'ZM': '['
            ,'ZN': ']'
            ,'ZC': ':'
            ,'ZZ': 'Z'
            ,'zz': 'z'
            ,'za': '&'
            ,'zb': '|'
            ,'zc': '^'
            ,'zd': '$'
            ,'ze': '='
            ,'zg': '>'
            ,'zh': '#'
            ,'zi': '.'
            ,'zl': '<'
            ,'zm': '-'
            ,'zn': '!'
            ,'zp': '+'
            ,'zq': '\''
            ,'zr': '\\'
            ,'zs': '/'
            ,'zt': '*'
            ,'zu': '_'
            ,'zv': '%'}

def decode_z_str(str):
    str2 = ''
    splits = re.split('([zZ].)', str)
    for split in splits:
        if len(split) == 2 and (split[0] == 'Z' or split[0] == 'z'):
            str2 += z_decoder.get(split, split[1])
        else:
            str2 += split

    return str2

def __lldb_init_module(debugger, session_dict):
    debugger.HandleCommand("command script add -f ghc.print_obj_dbg printObj")
    debugger.HandleCommand("command script add -f ghc.print_base_reg printBaseReg")
    debugger.HandleCommand("command script add -f ghc.print_current_tso printCurrentTSO")
    debugger.HandleCommand("type synthetic add StgClosure_ --python-class ghc.SyntheticClosureProvider")
    debugger.HandleCommand("type synthetic add StgInfoTable_ --python-class ghc.SyntheticInfoTableProvider")
    return None

closure_print_map = {'CONSTR':               Constructor
                    ,'CONSTR_1_0':           Constructor
                    ,'CONSTR_0_1':           Constructor
                    ,'CONSTR_2_0':           Constructor
                    ,'CONSTR_1_1':           Constructor
                    ,'CONSTR_0_2':           Constructor
                    ,'CONSTR_STATIC':        Constructor
                    ,'CONSTR_NOCAF_STATIC':  Constructor
                    ,'FUN':                  Function
                    ,'FUN_1_0':              Function
                    ,'FUN_0_1':              Function
                    ,'FUN_2_0':              Function
                    ,'FUN_1_1':              Function
                    ,'FUN_0_2':              Function
                    ,'FUN_STATIC':           Function
                    ,'THUNK':                Thunk
                    ,'THUNK_1_0':            Thunk
                    ,'THUNK_0_1':            Thunk
                    ,'THUNK_2_0':            Thunk
                    ,'THUNK_1_1':            Thunk
                    ,'THUNK_0_2':            Thunk
                    ,'THUNK_STATIC':         Thunk
                    ,'THUNK_SELECTOR':       Selector
                    ,'BCO':                  BCO
                    ,'AP':                   AP
                    ,'PAP':                  PAP
                    ,'AP_STACK':             AP_STACK
                    ,'IND':                  Ind
                    ,'IND_PERM':             Ind
                    ,'IND_STATIC':           IndStatic
                    ,'RET_BCO ':             BCO
                    ,'RET_SMALL':            RetSmall
                    ,'RET_BIG':              RetBig
                    ,'RET_DYN':              RetDyn
                    ,'RET_FUN ':             RetFun
                    ,'UPDATE_FRAME':         UpdateFrame
                    ,'CATCH_FRAME':          CatchFrame
                    ,'UNDERFLOW_FRAME':      UnderflowFrame
                    ,'STOP_FRAME':           StopFrame
                    ,'BLOCKING_QUEUE':       BlockingQueue
                    ,'BLACKHOLE':            BlackHole
                    ,'MVAR_CLEAN':           MVar
                    ,'MVAR_DIRTY':           MVar
                    ,'ARR_WORDS':            Array
                    ,'MUT_ARR_PTRS_CLEAN':   MutableArray
                    ,'MUT_ARR_PTRS_DIRTY':   MutableArray
                    ,'MUT_ARR_PTRS_FROZEN0': MutableArray
                    ,'MUT_ARR_PTRS_FROZEN':  MutableArray
                    ,'MUT_VAR_CLEAN':        IORef
                    ,'MUT_VAR_DIRTY':        IORef
                    ,'WEAK':                 WeakRef
                    ,'PRIM':                 Primitive
                    ,'MUT_PRIM':             MutablePrimitive
                    ,'TSO':                  TSO
                    ,'STACK':                Stack
                    ,'TREC_CHUNK':           TRecChunk
                    ,'ATOMICALLY_FRAME':     AtomicallyFrame
                    ,'CATCH_RETRY_FRAME':    CatchRetryFrame
                    ,'CATCH_STM_FRAME':      CatchSTMFrame
                    ,'WHITEHOLE':            Ind}

