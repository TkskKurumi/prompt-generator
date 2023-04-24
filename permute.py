from __future__ import annotations
from functools import partial
from typing import List
import random
from math import ceil
class Node:
    def __init__(self, func=None, name="unknown"):
        self.to = []
        self.func = func
        self.name = name
    def connect(self, other: Node):
        self.to.append(other)
        return other
    def __repr__(self):
        return "<Node name=%s>"%(self.name)
class Block:
    def __init__(self):
        self.head = Node()
        self.tail = Node()
    def __repr__(self):
        return "<Block %s-%s>"%(self.head.name, self.tail.name)
class Branch(Block):
    def __init__(self, contents: List[Block]):
        super().__init__()
        for i in contents:
            self.head.connect(i.head)
            i.tail.connect(self.tail)

class Concat(Block):
    def __init__(self, contents: List[Block]):
        super().__init__()
        last = None
        for i in contents:
            if(last):
                last.tail.connect(i.head)
            else:
                self.head.connect(i.head)
            last = i
        last.tail.connect(self.tail)
class Single(Block):
    def __init__(self, content: Node):
        super().__init__()
        self.head.connect(content).connect(self.tail)

class Status:
    def __init__(self, texts=None, sub=None):
        self.texts = [] if texts is None else texts
        self.sub = {} if sub is None else sub
    # def copy(self):
    #     return Status(list(self.texts), dict(self.sub))
def _add_text(text, S):
    S.texts.append(text)
def _set_sub(*args):
    S = args[-1]
    for i in range(1, len(args)-1, 2):
        S.sub[args[i-1]] = args[i]

def Build(ls, route=None) -> Block:
    if(route is None):
        route = []
    nm = "_".join(["%s"%i for i in route])
    if(isinstance(ls, list)):
        typ = ls[0]
        if(typ.startswith("sub")):
            f = partial(_set_sub, *ls[1:])
            node = Node(func=f, name="sub_"+nm)
            ret = Single(node)
            ret.head.name = node.name+"_pre"
            ret.tail.name = node.name+"_post"
            return ret
        elif(typ.startswith("branch")):
            contents = []
            for idx, i in enumerate(ls[1:]):
                route.append(idx)
                contents.append(Build(i, route))
                route.pop()
            ret = Branch(contents)
            ret.head.name = "branch_h_"+nm
            ret.tail.name = "branch_t_"+nm
            return ret
        elif(typ.startswith("concat")):
            contents = []
            for idx, i in enumerate(ls[1:]):
                route.append(idx)
                contents.append(Build(i, route))
                route.pop()
            ret = Concat(contents)
            ret.head.name = "concat_"+nm+"_h"
            ret.tail.name = "concat_"+nm+"_t"
            return ret
        else:
            raise TypeError(typ)
    elif(isinstance(ls, str)):
        f = partial(_add_text, ls)
        node = Node(name="text_"+nm, func=f)
        ret = Single(node)
        ret.head.name = nm+"_pre"
        ret.tail.name = nm+"_post"
        return ret
    else:
        raise TypeError(type(ls))
    
def get_texts(ls, mx=2048):
    if(isinstance(ls, list)):
        top = Build(ls)
    elif(isinstance(ls, Block)):
        top = ls
    else:
        raise TypeError(type(ls))
    end = top.tail
    stack = []
    ret = []
    def out():
        nonlocal stack, ret
        S = Status()
        for i in stack:
            if(i.func is not None):
                i.func(S)
        texts = []
        for t in S.texts:
            while(True):
                stop = True
                for k, v in S.sub.items():
                    if(k in t):
                        t = t.replace(k, v)
                        stop = False
                if(stop):
                    break
            texts.append(t)
        # print(stack, texts)
        ret.append("".join(texts))
    def recur(u: Node, max_branch):
        nonlocal stack, end
        if(u is end):
            out()
        for v in stack:
            assert v is not u, "%s %s"%(stack, u)
        stack.append(u)
        to = u.to
        if(len(to)>max_branch):
            to = random.sample(to, max(1, ceil(max_branch)))
        for v in to:
            recur(v, max_branch/len(to))
            # if(len(ret)>mx):break
        stack.pop()
    recur(top.head, mx)
    return ret


    
    