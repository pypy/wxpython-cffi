import etgtools
import etgtools.tweaker_tools as tools

from etgtools import ModuleDef, EnumDef, EnumValueDef, ClassDef, ParamDef

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "stockgdi"   # Base name of the file to generate to for this script
DOCSTRING = ""

def run():
    module = ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)

    c = ClassDef(name="wxStockGDI")

    e = EnumDef(name="Item", protection='public')
    e.addItem(EnumValueDef(name="BRUSH_BLACK"))
    e.addItem(EnumValueDef(name="BRUSH_BLUE"))
    e.addItem(EnumValueDef(name="BRUSH_CYAN"))
    e.addItem(EnumValueDef(name="BRUSH_GREEN"))
    e.addItem(EnumValueDef(name="BRUSH_YELLOW"))
    e.addItem(EnumValueDef(name="BRUSH_GREY"))
    e.addItem(EnumValueDef(name="BRUSH_LIGHTGREY"))
    e.addItem(EnumValueDef(name="BRUSH_MEDIUMGREY"))
    e.addItem(EnumValueDef(name="BRUSH_RED"))
    e.addItem(EnumValueDef(name="BRUSH_TRANSPARENT"))
    e.addItem(EnumValueDef(name="BRUSH_WHITE"))
    e.addItem(EnumValueDef(name="COLOUR_BLACK"))
    e.addItem(EnumValueDef(name="COLOUR_BLUE"))
    e.addItem(EnumValueDef(name="COLOUR_CYAN"))
    e.addItem(EnumValueDef(name="COLOUR_GREEN"))
    e.addItem(EnumValueDef(name="COLOUR_YELLOW"))
    e.addItem(EnumValueDef(name="COLOUR_LIGHTGREY"))
    e.addItem(EnumValueDef(name="COLOUR_RED"))
    e.addItem(EnumValueDef(name="COLOUR_WHITE"))
    e.addItem(EnumValueDef(name="CURSOR_CROSS"))
    e.addItem(EnumValueDef(name="CURSOR_HOURGLASS"))
    e.addItem(EnumValueDef(name="CURSOR_STANDARD"))
    e.addItem(EnumValueDef(name="FONT_ITALIC"))
    e.addItem(EnumValueDef(name="FONT_NORMAL"))
    e.addItem(EnumValueDef(name="FONT_SMALL"))
    e.addItem(EnumValueDef(name="FONT_SWISS"))
    e.addItem(EnumValueDef(name="PEN_BLACK"))
    e.addItem(EnumValueDef(name="PEN_BLACKDASHED"))
    e.addItem(EnumValueDef(name="PEN_BLUE"))
    e.addItem(EnumValueDef(name="PEN_CYAN"))
    e.addItem(EnumValueDef(name="PEN_GREEN"))
    e.addItem(EnumValueDef(name="PEN_YELLOW"))
    e.addItem(EnumValueDef(name="PEN_GREY"))
    e.addItem(EnumValueDef(name="PEN_LIGHTGREY"))
    e.addItem(EnumValueDef(name="PEN_MEDIUMGREY"))
    e.addItem(EnumValueDef(name="PEN_RED"))
    e.addItem(EnumValueDef(name="PEN_TRANSPARENT"))
    e.addItem(EnumValueDef(name="PEN_WHITE"))
    c.addItem(e)


    c.addMethod(
        '', 'wxStockGDI', '()', isCtor=True)
    c.addMethod(
        '', '~wxStockGDI', '()', isDtor=True, isVirtual=True)

    c.addMethod(
        'void', 'DeleteAll', '()', isStatic=True)

    c.addMethod(
        'wxStockGDI&', 'instance', '()', isStatic=True)

    c.addMethod(
        'const wxBrush*', 'GetBrush', '(Item item)', isStatic=True,
        items=[ParamDef(type='Item', name='item')])
    c.addMethod(
        'const wxColour*', 'GetColour', '(Item item)', isStatic=True,
        items=[ParamDef(type='Item', name='item')])
    c.addMethod(
        'const wxCursor*', 'GetCursor', '(Item item)', isStatic=True,
        items=[ParamDef(type='Item', name='item')])
    c.addMethod(
        'const wxPen*', 'GetPen', '(Item item)', isStatic=True,
        items=[ParamDef(type='Item', name='item')])

    c.addMethod(
        'const wxFont*', 'GetFont', '(Item item)',
        items=[ParamDef(type='Item', name='item')])

    c.addPrivateCopyCtor()
    c.addPrivateAssignOp()

    # Add some methods for fetching the various global gdi object lists so
    # they can be set at app creation time too.   
    c.addCppMethod(
        'wxFontList*', '_getTheFontList', '()', isStatic=True,
        body="return wxTheFontList;")

    c.addCppMethod(
        'wxPenList*', '_getThePenList', '()', isStatic=True,
        body="return wxThePenList;")

    c.addCppMethod(
        'wxBrushList*', '_getTheBrushList', '()', isStatic=True,
        body="return wxTheBrushList;")

    c.addCppMethod(
        'wxColourDatabase*', '_getTheColourDatabase', '()', isStatic=True,
        body="return wxTheColourDatabase;")

    module.addPyCode("""\
    def _initStockObjects():
        import wx
        wx.NORMAL_FONT._copyFrom(       StockGDI.instance().GetFont(StockGDI.FONT_NORMAL))
        wx.SMALL_FONT._copyFrom(        StockGDI.instance().GetFont(StockGDI.FONT_SMALL))
        wx.SWISS_FONT._copyFrom(        StockGDI.instance().GetFont(StockGDI.FONT_SWISS))
        wx.ITALIC_FONT._copyFrom(       StockGDI.instance().GetFont(StockGDI.FONT_ITALIC))
                                            
        wx.BLACK_DASHED_PEN._copyFrom(  StockGDI.GetPen(StockGDI.PEN_BLACKDASHED))
        wx.BLACK_PEN._copyFrom(         StockGDI.GetPen(StockGDI.PEN_BLACK))
        wx.BLUE_PEN._copyFrom(          StockGDI.GetPen(StockGDI.PEN_BLUE))
        wx.CYAN_PEN._copyFrom(          StockGDI.GetPen(StockGDI.PEN_CYAN))
        wx.GREEN_PEN._copyFrom(         StockGDI.GetPen(StockGDI.PEN_GREEN))
        wx.YELLOW_PEN._copyFrom(        StockGDI.GetPen(StockGDI.PEN_YELLOW))
        wx.GREY_PEN._copyFrom(          StockGDI.GetPen(StockGDI.PEN_GREY))
        wx.LIGHT_GREY_PEN._copyFrom(    StockGDI.GetPen(StockGDI.PEN_LIGHTGREY))
        wx.MEDIUM_GREY_PEN._copyFrom(   StockGDI.GetPen(StockGDI.PEN_MEDIUMGREY))
        wx.RED_PEN._copyFrom(           StockGDI.GetPen(StockGDI.PEN_RED))
        wx.TRANSPARENT_PEN._copyFrom(   StockGDI.GetPen(StockGDI.PEN_TRANSPARENT))
        wx.WHITE_PEN._copyFrom(         StockGDI.GetPen(StockGDI.PEN_WHITE))

        wx.BLACK_BRUSH._copyFrom(       StockGDI.GetBrush(StockGDI.BRUSH_BLACK))
        wx.BLUE_BRUSH._copyFrom(        StockGDI.GetBrush(StockGDI.BRUSH_BLUE))
        wx.CYAN_BRUSH._copyFrom(        StockGDI.GetBrush(StockGDI.BRUSH_CYAN))
        wx.GREEN_BRUSH._copyFrom(       StockGDI.GetBrush(StockGDI.BRUSH_GREEN))
        wx.YELLOW_BRUSH._copyFrom(      StockGDI.GetBrush(StockGDI.BRUSH_YELLOW))
        wx.GREY_BRUSH._copyFrom(        StockGDI.GetBrush(StockGDI.BRUSH_GREY))
        wx.LIGHT_GREY_BRUSH._copyFrom(  StockGDI.GetBrush(StockGDI.BRUSH_LIGHTGREY))
        wx.MEDIUM_GREY_BRUSH._copyFrom( StockGDI.GetBrush(StockGDI.BRUSH_MEDIUMGREY))
        wx.RED_BRUSH._copyFrom(         StockGDI.GetBrush(StockGDI.BRUSH_RED))
        wx.TRANSPARENT_BRUSH._copyFrom( StockGDI.GetBrush(StockGDI.BRUSH_TRANSPARENT))
        wx.WHITE_BRUSH._copyFrom(       StockGDI.GetBrush(StockGDI.BRUSH_WHITE))

        wx.BLACK._copyFrom(             StockGDI.GetColour(StockGDI.COLOUR_BLACK))
        wx.BLUE._copyFrom(              StockGDI.GetColour(StockGDI.COLOUR_BLUE))
        wx.CYAN._copyFrom(              StockGDI.GetColour(StockGDI.COLOUR_CYAN))
        wx.GREEN._copyFrom(             StockGDI.GetColour(StockGDI.COLOUR_GREEN))
        wx.YELLOW._copyFrom(            StockGDI.GetColour(StockGDI.COLOUR_YELLOW))
        wx.LIGHT_GREY._copyFrom(        StockGDI.GetColour(StockGDI.COLOUR_LIGHTGREY))
        wx.RED._copyFrom(               StockGDI.GetColour(StockGDI.COLOUR_RED))
        wx.WHITE._copyFrom(             StockGDI.GetColour(StockGDI.COLOUR_WHITE))

        wx.CROSS_CURSOR._copyFrom(      StockGDI.GetCursor(StockGDI.CURSOR_CROSS))
        wx.HOURGLASS_CURSOR._copyFrom(  StockGDI.GetCursor(StockGDI.CURSOR_HOURGLASS))
        wx.STANDARD_CURSOR._copyFrom(   StockGDI.GetCursor(StockGDI.CURSOR_STANDARD))

        wx.TheFontList       = StockGDI._getTheFontList()
        wx.ThePenList        = StockGDI._getThePenList()
        wx.TheBrushList      = StockGDI._getTheBrushList()
        wx.TheColourDatabase = StockGDI._getTheColourDatabase()

    StockGDI._initStockObjects = staticmethod(_initStockObjects)
    """)

    module.addItem(c)

    tools.doCommonTweaks(module)
    tools.runGenerators(module)

if __name__ == '__main__':
    run()
