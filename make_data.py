from glob import glob
from os import path
from functools import partial
import json, random, os, sys, traceback
from permute import get_texts as Permute
from json.decoder import JSONDecodeError

def csv_dialogs(ipath):
    sub = ipath+".sub"
    with open(sub, "r") as f:
        sub = json.load(f)
    with open(ipath, "r") as f:
        lines = f.readlines()
    contents = ["branch"]
    for ln in lines:
        ls = ln.split(",")
        ask = ls[0]
        ans = ls[1]
        content = "<user><sep>"+ask+"<lf><bot><sep>"+ans
        contents.append(content)
    sub.append(contents)
    return Permute(sub)
def json_dialogs(ipath):
    with open(ipath) as f:
        contents = json.load(f)
    def permute(func, stack, to_permute, index=0):
        n = len(to_permute)
        if(index == n):
            func(*stack)
        else:
            for i in to_permute[index]:
                stack.append(i)
                permute(func, stack, to_permute, index+1)
                stack.pop()
    
    def foo(item):
        ret = []
        sub = {}
        def f_permuted_contents(*result):
            nonlocal ret
            res = []
            for i in result:
                flag = True
                while(flag):
                    flag = False
                    for k, v in sub.items():
                        if(k in i):
                            i = i.replace(k, v)
                            flag = True
                res.append(i)
            for join in item.get("join", "\n"):
                ret.append(join.join(res))
        def permute_contents():
            nonlocal sub, ret
            contents = item.get("contents")
            for idx, i in enumerate(contents):
                if(isinstance(i, dict)):
                    contents[idx] = foo(i)
                elif(isinstance(i, list)):
                    contents[idx] = i
                else:
                    contents[idx] = [i]
            permute(f_permuted_contents, [], contents, 0)
        def f_permuted_sub(keyss, *result):
            nonlocal sub, ret
            
            for idx, keys in enumerate(keyss):
                for jdx, key in enumerate(keys):
                    sub[key] = result[idx][jdx]
            permute_contents()    
        def permute_sub():
            subs = item.get("substitudes", [])
            keyss, candidatess =[], []
            for i in subs:
                keys = i["keys"]
                candidates = i["choice"]
                keyss.append(keys)
                candidatess.append(candidates)
            
            permute(partial(f_permuted_sub, keyss), [], candidatess)
        permute_sub()
        if(item.get("max")):
            if(len(ret)>item["max"]):
                ret = random.sample(ret, item["max"])
        elif(len(ret)>100):
            print("some sample has larger branch than 100")
        return ret
    
    ret = []
    for i in contents:
        ret.extend(foo(i))
    return ret

_default_users = ["branch",
    ["sub", "<user>", "User", "<bot>", "Bot"],
    ["sub", "<user>", "Bob", "<bot>", "Alice"]
]
_default_lf = ["branch",
    ["sub", "<lf>", "\n"],
    ["sub", "<lf>", "\n\n"]
]
_default_sep = ["branch",
    ["sub", "<sep>", ": "],
    ["sub", "<sep>", "\uff1a"]
]

def ijson(pth):
    ret = []
    with open(pth, "r") as f:
        while(len(ret)<4096):
            try:
                ln = f.readline()
            except EOFError:
                break
            ln = ln.strip("\n\r")
            j = json.loads(ln)
            Q = j["instruction"]+j.get("input", "")
            A = j["output"]
            ls = ["concat",
                _default_users,
                _default_lf,
                _default_sep,
                "<user><sep>", Q, "<lf>",
                "<bot><sep>", A, "<lf>",
                "<user><sep>"
            ]
            dialogs = Permute(ls)
            ret.extend(dialogs)
    return ret
            

def txt_dialogs(ipath):
    with open(ipath) as f:
        lines = f.readlines()
    _lines = []
    for i in lines:
        i = i.strip("\n\r ")
        if(i):
            _lines.append(i)

    def permute(ret, stack, to_permute, index):
        n = len(to_permute)
        if(index == n):
            ret.append("\n".join(stack))
        else:
            for i in to_permute[index]:
                stack.append(i)
                permute(ret, stack, to_permute, index+1)
                stack.pop()
    lines = _lines
    dialogs = []
    dialog = []
    senders = set()
    sender = None
    append_to = None
    for i in lines:
        if(i==">End"):
            for sep in [": ", "："]:
                dlgs = []
                for sender, choices in dialog:
                    _dlgs = []
                    for choice in choices:
                        if(sender):
                            _dlgs.append(sep.join([sender, choice]))
                        else:
                            _dlgs.append(choice)
                    dlgs.append(_dlgs)
                permute(dialogs, [], dlgs, 0)
            dialog = []
            sender = None
        elif(i.startswith(">")):
            _sender = i[1:]
            if(_sender!=sender):
                sender = _sender
                dialog.append([sender, [""]])
                append_to = dialog[-1][-1]
                senders.add(sender)
        elif(i=="|"):
            append_to.append("")
        else:
            if(append_to[-1]):
                append_to[-1] = append_to[-1]+"\n"+i
            else:
                append_to[-1] = i
    return dialogs
if (__name__=="__main__"):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", type=str)
    parser.add_argument("-O", "--output", type=str)
    parser.add_argument("--max_per_file", type=int, help="max number of entries per file.", default=4096)
    args = parser.parse_args()
    f = open(args.output, "w", encoding="utf-8")
    prt = partial(print, file=f)

    max_per_file = args.max_per_file

    for i in os.listdir(args.input_dir):
        pth = path.join(args.input_dir, i)
        ext = path.splitext(pth)[-1]
        if (ext==".permute"):
            with open(pth, encoding="utf-8") as infile:
                try:
                    ls = json.load(infile)
                except JSONDecodeError as e:
                    traceback.print_exc()
                    print("Error decoding %s (%s:%s)"%(pth, pth, e.lineno))
                    continue
            try:
                dialogs = Permute(ls, mx=max_per_file)
            except Exception as e:
                traceback.print_exc()
                print("Error permuting %s, %s"%(pth, e))
                continue
            dialogs = [i for i in dialogs if i] # maybe empty
            le = len(dialogs)
            for t in dialogs:
                prt(json.dumps({"text": t}, ensure_ascii=False))
        elif (ext==".jsonl"):
            with open(pth) as infile:
                lines = infile.readlines()[:max_per_file]
            le = len(lines)
            f.write("".join(lines))
        elif(ext==".ijson"):
            dialogs = ijson(pth)[:max_per_file]
            le = len(dialogs)
            for t in dialogs:
                prt(json.dumps({"text": t}, ensure_ascii=False))
        else:
            print("Unrecognized", pth)
            continue
        print("%d entries from %s"%(le, pth))
