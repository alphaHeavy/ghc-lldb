import lldb

closure_name_map = {0:  'INVALID_OBJECT'
                   ,1:  'CONSTR'
                   ,2:  'CONSTR_1_0'
                   ,3:  'CONSTR_0_1'
                   ,4:  'CONSTR_2_0'
                   ,5:  'CONSTR_1_1'
                   ,6:  'CONSTR_0_2'
                   ,7:  'CONSTR_STATIC'
                   ,8:  'CONSTR_NOCAF_STATIC'
                   ,9:  'FUN'
                   ,10: 'FUN_1_0'
                   ,11: 'FUN_0_1'
                   ,12: 'FUN_2_0'
                   ,13: 'FUN_1_1'
                   ,14: 'FUN_0_2'
                   ,15: 'FUN_STATIC'
                   ,16: 'THUNK'
                   ,17: 'THUNK_1_0'
                   ,18: 'THUNK_0_1'
                   ,19: 'THUNK_2_0'
                   ,20: 'THUNK_1_1'
                   ,21: 'THUNK_0_2'
                   ,22: 'THUNK_STATIC'
                   ,23: 'THUNK_SELECTOR'
                   ,24: 'BCO'
                   ,25: 'AP'
                   ,26: 'PAP'
                   ,27: 'AP_STACK'
                   ,28: 'IND'
                   ,29: 'IND_PERM'
                   ,30: 'IND_STATIC'
                   ,31: 'RET_BCO '
                   ,32: 'RET_SMALL'
                   ,33: 'RET_BIG'
                   ,34: 'RET_DYN'
                   ,35: 'RET_FUN '
                   ,36: 'UPDATE_FRAME'
                   ,37: 'CATCH_FRAME'
                   ,38: 'UNDERFLOW_FRAME'
                   ,39: 'STOP_FRAME'
                   ,40: 'BLOCKING_QUEUE'
                   ,41: 'BLACKHOLE'
                   ,42: 'MVAR_CLEAN'
                   ,43: 'MVAR_DIRTY'
                   ,44: 'ARR_WORDS'
                   ,45: 'MUT_ARR_PTRS_CLEAN'
                   ,46: 'MUT_ARR_PTRS_DIRTY'
                   ,47: 'MUT_ARR_PTRS_FROZEN0'
                   ,48: 'MUT_ARR_PTRS_FROZEN'
                   ,49: 'MUT_VAR_CLEAN'
                   ,50: 'MUT_VAR_DIRTY'
                   ,51: 'WEAK'
                   ,52: 'PRIM'
                   ,53: 'MUT_PRIM'
                   ,54: 'TSO'
                   ,55: 'STACK '
                   ,56: 'TREC_CHUNK'
                   ,57: 'ATOMICALLY_FRAME'
                   ,58: 'CATCH_RETRY_FRAME'
                   ,59: 'CATCH_STM_FRAME'
                   ,60: 'WHITEHOLE'}

closure_type_map = {'CONSTR':               'StgClosure_'
                   ,'CONSTR_1_0':           'StgClosure_'
                   ,'CONSTR_0_1':           'StgClosure_'
                   ,'CONSTR_2_0':           'StgClosure_'
                   ,'CONSTR_1_1':           'StgClosure_'
                   ,'CONSTR_0_2':           'StgClosure_'
                   ,'CONSTR_STATIC':        'StgClosure_'
                   ,'CONSTR_NOCAF_STATIC':  'StgClosure_'
                   ,'FUN':                  'StgClosure_'
                   ,'FUN_1_0':              'StgClosure_'
                   ,'FUN_0_1':              'StgClosure_'
                   ,'FUN_2_0':              'StgClosure_'
                   ,'FUN_1_1':              'StgClosure_'
                   ,'FUN_0_2':              'StgClosure_'
                   ,'FUN_STATIC':           'StgClosure_'
                   ,'THUNK':                'StgThunk'
                   ,'THUNK_1_0':            'StgThunk'
                   ,'THUNK_0_1':            'StgThunk'
                   ,'THUNK_2_0':            'StgThunk'
                   ,'THUNK_1_1':            'StgThunk'
                   ,'THUNK_0_2':            'StgThunk'
                   ,'THUNK_STATIC':         'StgThunk'
                   ,'THUNK_SELECTOR':       'StgSelector'
                   ,'BCO':                  'StgBCO'
                   ,'AP':                   'StgAP'
                   ,'PAP':                  'StgPAP'
                   ,'AP_STACK':             'StgAP_STACK'
                   ,'IND':                  'StgInd'
                   ,'IND_PERM':             'StgInd'
                   ,'IND_STATIC':           'StgIndStatic'
                   # ,'RET_BCO ':
                   # ,'RET_SMALL':
                   # ,'RET_BIG':
                   # ,'RET_DYN':
                   # ,'RET_FUN ':
                   ,'UPDATE_FRAME':         'StgUpdateFrame'
                   ,'CATCH_FRAME':          'StgCatchFrame'
                   ,'UNDERFLOW_FRAME':      'StgUnderflowFrame'
                   ,'STOP_FRAME':           'StgStopFrame'
                   ,'BLOCKING_QUEUE':       'StgBlockingQueue'
                   ,'BLACKHOLE':            'StgInd'
                   ,'MVAR_CLEAN':           'StgMVar'
                   ,'MVAR_DIRTY':           'StgMVar'
                   ,'ARR_WORDS':            'StgArrWords'
                   ,'MUT_ARR_PTRS_CLEAN':   'StgMutArrPtrs'
                   ,'MUT_ARR_PTRS_DIRTY':   'StgMutArrPtrs'
                   ,'MUT_ARR_PTRS_FROZEN0': 'StgMutArrPtrs'
                   ,'MUT_ARR_PTRS_FROZEN':  'StgMutArrPtrs'
                   ,'MUT_VAR_CLEAN':        'StgMutVar'
                   ,'MUT_VAR_DIRTY':        'StgMutVar'
                   ,'WEAK':                 'StgWeak'
                   # ,'PRIM':
                   # ,'MUT_PRIM':
                   ,'TSO':                  'StgTSO'
                   # ,'STACK ':
                   ,'TREC_CHUNK':           'StgTRecChunk'
                   ,'ATOMICALLY_FRAME':     'StgAtomicallyFrame'
                   ,'CATCH_RETRY_FRAME':    'StgCatchRetryFrame'
                   ,'CATCH_STM_FRAME':      'StgCatchSTMFrame'
                   ,'WHITEHOLE':            'StgInd'}

def closure_type_name(tag):
    name = closure_name_map[tag]
    return closure_type_map[name]

def untag_closure(obj):
    # TODO: untag for integers and pointers
    closure_type = lldb.debugger.GetSelectedTarget().FindFirstType('StgClosure_')
    return obj.CreateValueFromAddress(obj.GetName() + '_closure', obj.GetValueAsUnsigned() & ~7, closure_type)

def get_info_table_from_closure(obj):
    target = lldb.debugger.GetSelectedTarget()
    # lldb doesn't support negative subscripts, this would be cleaner as '.header.info[-1]'
    info_table = obj.GetValueForExpressionPath('.header.info')
    info_table_sym = target.ResolveSymbolContextForAddress(info_table.GetAddress(), lldb.eSymbolContextSymbol).GetSymbol()
    # sym.GetStartAddress().GetLoadAddress(target)
    # cast it back ot the info table
    stg_info_table_type = target.FindFirstType('StgInfoTable_')
    return info_table.CreateValueFromAddress(info_table.GetName() + '_info', info_table.GetValueAsUnsigned() - 16, stg_info_table_type)

def cast_closure(obj):
    obj = untag_closure(obj)
    info_table = get_info_table_from_closure(obj)
    closure_type = info_table.GetChildMemberWithName('type')
    type_name = closure_type_name(closure_type.GetValueAsUnsigned())
    target = lldb.debugger.GetSelectedTarget()
    closure_type = target.FindFirstType(type_name)
    return obj.Cast(closure_type)

