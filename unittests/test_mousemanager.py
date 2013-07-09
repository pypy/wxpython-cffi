import imp_unittest, unittest
import wtc
import wx
import sys

# Is it just this module or the whole test suite being run?
runningStandalone = False  

#---------------------------------------------------------------------------

class mousemanager_Tests(wtc.WidgetTestCase):

    def test_mousemanager1(self):
        class MyMEM(wx.MouseEventsManager):
            def MouseHitTest(self, pos):
                self.hitTest = pos
                return 1
            def MouseClicked(self, item):
                self.mouseClicked = item
                return True
            def MouseDragBegin(self, item, pos):
                return False
            def MouseDragging(self, item, pos):
                pass
            def MouseDragEnd(self, item, pos):
                pass
            def MouseDragCancelled(self, item):
                pass
            def MouseClickBegin(self, item):
                pass
            def MouseClickCancelled(self, item):
                pass
        
        pnl = wx.Panel(self.frame, size=(50,50))
        mm = MyMEM(pnl)
        self.myYield()
        
        if sys.platform == 'darwin' and not runningStandalone:
            return
        
        uia = wx.UIActionSimulator()
        uia.MouseMove(pnl.ClientToScreen((10,10)))
        self.myYield()
        uia.MouseClick()
        self.myYield()
        
        self.assertTrue(hasattr(mm, 'hitTest'))
        self.assertTrue(hasattr(mm, 'mouseClicked'))
        
        
#---------------------------------------------------------------------------

if __name__ == '__main__':
    runningStandalone = True
    unittest.main()
