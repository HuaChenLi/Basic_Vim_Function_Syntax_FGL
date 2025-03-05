import vim # type: ignore

def highlightConstant(token):
    vim.command("execute 'syn match constantGroup /\\<" + token + "\\>/'")