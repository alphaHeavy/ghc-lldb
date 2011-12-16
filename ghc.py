import lldb
import ghc_map

# (lldb) command script import '/Source/ghc-lldb/ghc.py'

class SyntheticClosureProvider(object):
    def __init__(self, valobj, dict):
        self.valobj = valobj
        print dir(valobj)
        print valobj.CreateChildAtOffset('foo', 0, valobj.GetType()).AddressOf().AddressOf()
        self.closure = Closure.get(lldb.debugger, valobj)
        self.update()

    def num_children(self):
        return len(self.closure.payload)

    def get_child_index(self, name):
        try:
            return int(name.lstrip('[').rstrip(']'))
        except:
            return -1;

    def get_child_at_index(self,index):
        return self.closure.payload[index]

    def update(self):
        # self.closure = Closure.get(valobj) ?
        pass

class Closure(object):
    def __init__(self, debugger, obj):
        self.debugger = debugger
        self.obj = obj
        self.payload = []

    # def __str__(self):
    #   return str(self.info_table()) + ' ' + str(self.payload)

    def __repr__(self):
        return '<Closure info_table:{0} payload:{1}>'.format(self.info_table(), self.payload)

    def reify(self):
        info = self.info_table().info_table
        ptrs = info.GetValueForExpressionPath('.layout.payload.ptrs').GetValueAsUnsigned()
        nptrs = info.GetValueForExpressionPath('.layout.payload.nptrs').GetValueAsUnsigned()

        # lldb does bounds checks on array subscripts, which doesn't work with GHC's closure types
        # so strip the StgClosure[1] type of the array size, leaving StgClosure* (which is not bounds checked)
        payload = self.obj.GetValueForExpressionPath('.payload[0]').AddressOf()

        i = 0
        while i < ptrs:
            payload_i = payload.GetValueForExpressionPath('[' + str(i) + ']')
            self.payload.append(Closure.get(self.debugger, payload_i))
            i += 1

        while i < ptrs+nptrs:
            payload_i = payload.GetValueForExpressionPath('[' + str(i) + ']')
            self.payload.append(payload_i.GetValueAsUnsigned())
            i += 1

    @staticmethod
    def untag(debugger, obj):
        # TODO: untag for integers and pointers
        closure_type = find_first_type(debugger, 'StgClosure_')
        return obj.CreateValueFromAddress(obj.GetName() + '_closure', obj.GetValueAsUnsigned() & ~7, closure_type)

    def info_table(self):
        target = self.debugger.GetSelectedTarget()
        header = self.obj.GetValueForExpressionPath('.header') # TODO: remove
        # lldb doesn't support negative subscripts, this would be cleaner as '.header.info[-1]'
        info_table = self.obj.GetValueForExpressionPath('.header.info')
        info_table_sym = target.ResolveSymbolContextForAddress(info_table.Dereference().GetAddress(), lldb.eSymbolContextSymbol).GetSymbol()
        # sym.GetStartAddress().GetLoadAddress(target)
        # cast it back to the info table
        stg_info_table_type = find_first_type(self.debugger, 'StgInfoTable_')
        offset_info_table = info_table.CreateValueFromAddress(info_table_sym.GetName(), info_table.GetValueAsUnsigned() - 16, stg_info_table_type)
        return InfoTable(self.debugger, offset_info_table)

    @staticmethod
    def type_name(tag):
        name = ghc_map.closure_name_map[tag]
        return ghc_map.closure_type_map[name]

    @staticmethod
    def get(debugger, obj):
        obj = Closure.untag(debugger, obj)
        self = Closure(debugger, obj)

        info_table = self.info_table()
        closure_type = info_table.type()
        type_tag = closure_type.GetValueAsUnsigned()
        type_name = Closure.type_name(type_tag)
        target = debugger.GetSelectedTarget()
        closure_type = find_first_type(debugger, type_name)
        # propagate the constructor desciption or info table name to the closure
        closure = closure_print_map[ghc_map.closure_name_map[type_tag]](debugger, obj.CreateValueFromAddress(str(info_table), obj.GetLoadAddress(), closure_type))
        # closure = Closure(debugger, obj.CreateValueFromAddress(str(info_table), obj.GetLoadAddress(), closure_type))
        closure.reify()
        return closure
        # obj.CreateChildAtOffset(name, 0, closure_type)

    @staticmethod
    def get_expression(expr):
        frame = lldb.thread.GetSelectedFrame()
        obj = frame.EvaluateExpression(expr)
        return Closure.get(lldb.debugger, obj)

class Constructor(Closure):
    def __init__(self, debugger, obj):
        super(Constructor, self).__init__(debugger, obj)

class Function(Closure):
    def __init__(self, debugger, obj):
        super(Function, self).__init__(debugger, obj)

class Thunk(Closure):
    def __init__(self, debugger, obj):
        super(Thunk, self).__init__(debugger, obj)

class Selector(Closure):
    def __init__(self, debugger, obj):
        super(Selector, self).__init__(debugger, obj)

class BCO(Closure):
    def __init__(self, debugger, obj):
        super(BCO, self).__init__(debugger, obj)

class AP(Closure):
    def __init__(self, debugger, obj):
        super(AP, self).__init__(debugger, obj)

class PAP(Closure):
    def __init__(self, debugger, obj):
        super(PAP, self).__init__(debugger, obj)

class AP_STACK(Closure):
    def __init__(self, debugger, obj):
        super(AP_STACK, self).__init__(debugger, obj)

class Indirection(Closure):
    def __init__(self, debugger, obj):
        super(Indirection, self).__init__(debugger, obj)

class RetSmall(Closure):
    def __init__(self, debugger, obj):
        super(RetSmall, self).__init__(debugger, obj)

class RetBig(Closure):
    def __init__(self, debugger, obj):
        super(RetBig, self).__init__(debugger, obj)

class RetDyn(Closure):
    def __init__(self, debugger, obj):
        super(RetDyn, self).__init__(debugger, obj)

class RetFun(Closure):
    def __init__(self, debugger, obj):
        super(RetFun, self).__init__(debugger, obj)

class UpdateFrame(Closure):
    def __init__(self, debugger, obj):
        super(UpdateFrame, self).__init__(debugger, obj)

class CatchFrame(Closure):
    def __init__(self, debugger, obj):
        super(CatchFrame, self).__init__(debugger, obj)

class UnderflowFrame(Closure):
    def __init__(self, debugger, obj):
        super(UnderflowFrame, self).__init__(debugger, obj)

class StopFrame(Closure):
    def __init__(self, debugger, obj):
        super(StopFrame, self).__init__(debugger, obj)

class BlockingQueue(Closure):
    def __init__(self, debugger, obj):
        super(BlockingQueue, self).__init__(debugger, obj)

class BlackHole(Closure):
    def __init__(self, debugger, obj):
        super(BlackHole, self).__init__(debugger, obj)

class MVar(Closure):
    def __init__(self, debugger, obj):
        super(MVar, self).__init__(debugger, obj)

class Array(Closure):
    def __init__(self, debugger, obj):
        super(Array, self).__init__(debugger, obj)

class MutableArray(Closure):
    def __init__(self, debugger, obj):
        super(MutableArray, self).__init__(debugger, obj)

class IORef(Closure):
    def __init__(self, debugger, obj):
        super(IORef, self).__init__(debugger, obj)

class WeakRef(Closure):
    def __init__(self, debugger, obj):
        super(WeakRef, self).__init__(debugger, obj)

class Primitive(Closure):
    def __init__(self, debugger, obj):
        super(Primitive, self).__init__(debugger, obj)

class MutablePrimitive(Closure):
    def __init__(self, debugger, obj):
        super(MutablePrimitive, self).__init__(debugger, obj)

class TSO(Closure):
    def __init__(self, debugger, obj):
        super(TSO, self).__init__(debugger, obj)
        pass

class Stack(Closure):
    def __init__(self, debugger, obj):
        super(Stack, self).__init__(debugger, obj)

    def __repr__(self):
        return '<Stack stack_size:{0} dirty:{1} sp:{2} stack:{3}>'.format(self.stack_size.GetValueAsUnsigned(), self.dirty.GetValueAsUnsigned(), self.sp.GetValue(), self.stack.GetValue())

    def reify(self):
        super(Stack, self).reify()
        self.stack_size = self.obj.GetChildMemberWithName('stack_size')
        self.dirty = self.obj.GetChildMemberWithName('dirty')
        self.sp = self.obj.GetChildMemberWithName('sp')
        self.stack = self.obj.GetChildMemberWithName('stack')

class TRecChunk(Closure):
    def __init__(self, debugger, obj):
        super(TRecChunk, self).__init__(debugger, obj)

class AtomicallyFrame(Closure):
    def __init__(self, debugger, obj):
        super(AtomicallyFrame, self).__init__(debugger, obj)

class CatchRetryFrame(Closure):
    def __init__(self, debugger, obj):
        super(CatchRetryFrame, self).__init__(debugger, obj)

class CatchSTMFrame(Closure):
    def __init__(self, debugger, obj):
        super(CatchSTMFrame, self).__init__(debugger, obj)

class InfoTable(object):
    def __init__(self, debugger, info_table):
        self.debugger = debugger
        self.info_table = info_table

    # def __str__(self):
    #    return self.con_desc() or self.info_table.GetName()

    def __repr__(self):
        name = self.con_desc() or self.info_table.GetName()
        return '<InfoTable name:{0} entry:{1}>'.format(name, self.entry_symbol().GetName())

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
        return summary.strip('"') if summary else None

    def type(self):
        return self.info_table.GetChildMemberWithName('type')

    def entry_symbol(self):
        entry = self.info_table.AddressOf().GetValueForExpressionPath('[1]')
        target = self.debugger.GetSelectedTarget()
        return target.ResolveSymbolContextForAddress(entry.GetAddress(), lldb.eSymbolContextSymbol).GetSymbol()

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

def __lldb_init_module(debugger, session_dict):
    debugger.HandleCommand("command script add -f ghc.print_obj_dbg printObj")
    debugger.HandleCommand("command script add -f ghc.print_base_reg printBaseReg")
    debugger.HandleCommand("command script add -f ghc.print_current_tso printCurrentTSO")
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
                    ,'IND':                  Indirection
                    ,'IND_PERM':             Indirection
                    ,'IND_STATIC':           Indirection
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
                    ,'WHITEHOLE':            Indirection}


