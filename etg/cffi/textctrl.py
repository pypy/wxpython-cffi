def run(module):
    c = module.find('wxTextAttr')
    c.find('SetFont.flags').default = 'TEXT_ATTR_FONT &~TEXT_ATTR_FONT_PIXEL_SIZE'
