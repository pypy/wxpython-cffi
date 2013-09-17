def run(module):
    # TODO: replicate the methods from the sip/dc.py

    c = module.find('wxDC')
    # Replace defaults with values that can be evaluated by Python
    for overload in c.find('DrawLabel').all():
        overload.find('alignment').default = 'ALIGN_LEFT|ALIGN_TOP'
