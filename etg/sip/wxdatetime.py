def run(module):
    c = module.find('wxDateTime')
    c.addHeaderCode("#include <datetime.h>")
