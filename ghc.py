import lldb
import ghc_map

# (lldb) command script import '/Source/ghc-lldb/ghc.py'

class Closure(object):
    def __init__(self, debugger, obj):
        self.debugger = debugger
        self.obj = obj
        self.payload = []

    def __str__(self):
        return str(self.info_table()) + ' ' + str(self.payload)

    def __repr__(self):
        return str(self.info_table()) + ' ' + str(self.payload)

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
        type_name = Closure.type_name(closure_type.GetValueAsUnsigned())
        target = debugger.GetSelectedTarget()
        closure_type = find_first_type(debugger, type_name)
        # propagate the constructor desciption or info table name to the closure
        closure =  Closure(debugger, obj.CreateValueFromAddress(str(info_table), obj.GetLoadAddress(), closure_type))
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
        super(Closure, self).__init__(debugger, obj)
        pass

class Function(Closure):
    def __init__(self, debugger, obj):
        super(Closure, self).__init__(debugger, obj)
        pass

class Thunk(Closure):
    def __init__(self, debugger, obj):
        pass

class Selector(Closure):
    def __init__(self, debugger, obj):
        pass

class BCO(Closure):
    def __init__(self, debugger, obj):
        pass

class AP(Closure):
    def __init__(self, debugger, obj):
        pass

class PAP(Closure):
    def __init__(self, debugger, obj):
        pass

class Indirection(Closure):
    def __init__(self, debugger, obj):
        pass

class UpdateFrame(Closure):
    def __init__(self, debugger, obj):
        pass

class CatchFrame(Closure):
    def __init__(self, debugger, obj):
        pass

class UnderflowFrame(Closure):
    def __init__(self, debugger, obj):
        pass

class StopFrame(Closure):
    def __init__(self, debugger, obj):
        pass

class BlockingQueue(Closure):
    def __init__(self, debugger, obj):
        pass

class MVar(Closure):
    def __init__(self, debugger, obj):
        pass

class Array(Closure):
    def __init__(self, debugger, obj):
        pass

class MutableArray(Closure):
    def __init__(self, debugger, obj):
        pass

class IORef(Closure):
    def __init__(self, debugger, obj):
        pass

class WeakRef(Closure):
    def __init__(self, debugger, obj):
        pass

class Primitive(Closure):
    def __init__(self, debugger, obj):
        pass

class MutablePrimitive(Closure):
    def __init__(self, debugger, obj):
        pass

class TSO(Closure):
    def __init__(self, debugger, obj):
        pass

class Stack(Closure):
    def __init__(self, debugger, obj):
        pass

class TRecChunk(Closure):
    def __init__(self, debugger, obj):
        pass

class AtomicallyFrame(Closure):
    def __init__(self, debugger, obj):
        pass

class CatchRetryFrame(Closure):
    def __init__(self, debugger, obj):
        pass

class CatchSTMFrame(Closure):
    def __init__(self, debugger, obj):
        pass

class InfoTable(object):
    def __init__(self, debugger, info_table):
        self.debugger = debugger
        self.info_table = info_table

    def __str__(self):
        return self.con_desc() or self.info_table.GetName()

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

