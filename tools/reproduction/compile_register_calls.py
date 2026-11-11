"""Acyclic pure function calls lowered to the existing register instruction set.

Each helper is emitted once. Every call assigns its helper's return selector and
parameters, then jumps to its entry. Return dispatch uses CONST/JEQ/JUMP only.
The call graph is statically acyclic: an active helper's return selector cannot
be overwritten by a nested call to itself. No new semantic instruction is used.
"""
from __future__ import annotations
import ast
from compile_register import Compiler, allocate_registers


class SharedCallCompiler(Compiler):
    def __init__(self, source):
        super().__init__(source)
        self.helpers = {}
        self.queue = []
        graph={name:{node.func.id for node in ast.walk(fn)
                     if isinstance(node,ast.Call) and isinstance(node.func,ast.Name)}
               for name,fn in self.functions.items()}
        done=set()
        def visit(name,active):
            if name in active:
                raise ValueError('Recursive helper graph is forbidden')
            if name not in graph:
                raise ValueError('External function is forbidden')
            if name not in done:
                for callee in graph[name]:
                    visit(callee,active|{name})
                done.add(name)
        for name in graph:
            visit(name,set())

    def metadata(self,name):
        if name not in self.helpers:
            fn=self.functions[name]
            result_nodes=[n for n in ast.walk(fn) if isinstance(n,ast.Return)]
            result=result_nodes[0].value
            arity=len(result.elts) if isinstance(result,ast.Tuple) else 1
            self.helpers[name]={'outputs':[self.reg('$return_'+name,str(i)) for i in range(arity)],
                                'selector':self.reg('$selector',name),'sites':[], 'returns':[]}
            self.queue.append(name)
        return self.helpers[name]

    def call(self,name,args):
        if name not in self.functions:
            raise ValueError('External function is forbidden')
        fn=self.functions[name]
        if (fn.args.defaults or fn.args.kwonlyargs or fn.args.vararg or fn.args.kwarg or
                fn.args.posonlyargs or len(fn.args.args)!=len(args)):
            raise ValueError('Only positional matching-arity helper calls permitted')
        meta=self.metadata(name)
        for param,src in zip(fn.args.args,args):
            self.emit('COPY',dst=self.reg(name,param.arg),src=src)
        selector=len(meta['sites'])
        self.emit('CONST',dst=meta['selector'],value=str(selector))
        jump=self.emit('JUMP',next=-1)
        continuation=len(self.code)
        meta['sites'].append((jump,continuation))
        outputs=[self.temp() for _ in meta['outputs']]
        for dst,src in zip(outputs,meta['outputs']):
            self.emit('COPY',dst=dst,src=src)
        return outputs

    def compile(self,function,identifier,version='1.0'):
        fn=self.functions[function]
        inputs=[self.reg('$inputs',a.arg) for a in fn.args.args]
        outputs=self.call(function,inputs)
        if len(outputs)!=1:
            raise ValueError('Program entry must return one natural')
        self.emit('HALT')
        index=0
        while index<len(self.queue):
            name=self.queue[index]
            meta=self.helpers[name]
            meta['entry']=len(self.code)
            self.statements(self.functions[name].body,name,meta['outputs'],meta['returns'])
            index+=1
        for name in self.queue:
            meta=self.helpers[name]
            dispatcher=len(self.code)
            for site,_ in meta['sites']:
                self.code[site]['next']=meta['entry']
            for ret in meta['returns']:
                self.code[ret]['next']=dispatcher
            for selector,(_,continuation) in enumerate(meta['sites']):
                value=self.temp()
                self.emit('CONST',dst=value,value=str(selector))
                cond=self.emit('JEQ',left=meta['selector'],right=value,
                               **{'then':continuation,'else':-1})
                self.code[cond]['else']=len(self.code)
            # Unreachable for compiled source executions. An unknown selector
            # cannot fabricate a successful result by falling through to HALT.
            self.emit('JUMP',next=len(self.code))
        return {'id':identifier,'version':version,'register_count':len(self.registers),
                'inputs':inputs,'output':outputs[0],'entry':0,'instructions':self.code}


def compile_source_calls(source,function,identifier,version='1.0',optimize=True):
    program=SharedCallCompiler(source).compile(function,identifier,version)
    return allocate_registers(program) if optimize else program
