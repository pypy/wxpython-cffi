def run(module):
    module.addPyCode('''\
    import itertools''')

    c = module.find('wxDC')

    c.addPyMethod(
        '_DrawRectangleList', '(self, coords, pens, brushes)',
        body="""\
           for (coord, pen, brush) in itertools.izip_longest(
                   coords, pens, brushes):
               if pen is not None:
                   self.SetPen(pen)
               if brush is not None:
                   self.SetBrush(brush)
               self.DrawRectangle(*coord)
        """)

    c.addPyMethod(
        '_DrawEllipseList', '(self, coords, pens, brushes)',
        body="""\
           for (coord, pen, brush) in itertools.izip_longest(
                   coords, pens, brushes):
               if pen is not None:
                   self.SetPen(pen)
               if brush is not None:
                   self.SetBrush(brush)
               self.DrawEllipse(*coord)
        """)

    c.addPyMethod(
        '_DrawPolygonList', '(self, coords, pens, brushes)',
        body="""\
           for (coord, pen, brush) in itertools.izip_longest(
                   coords, pens, brushes):
               if pen is not None:
                   self.SetPen(pen)
               if brush is not None:
                   self.SetBrush(brush)
               self.DrawPolygon(coord)
        """)

    c.addPyMethod(
        '_DrawPointList', '(self, coords, pens, brushes)',
        body="""\
           for (coord, pen, brush) in itertools.izip_longest(
                   coords, pens, brushes):
               if pen is not None:
                   self.SetPen(pen)
               if brush is not None:
                   self.SetBrush(brush)
               self.DrawPoint(*coord)
        """)

    c.addPyMethod(
        '_DrawLineList', '(self, coords, pens, brushes)',
        body="""\
           for (coord, pen, brush) in itertools.izip_longest(
                   coords, pens, brushes):
               if pen is not None:
                   self.SetPen(pen)
               if brush is not None:
                   self.SetBrush(brush)
               self.DrawLine(*coord)
        """)

    c.addPyMethod(
        '_DrawTextList', '(self, texts, points, foregrounds, backgrounds)',
        body="""\
           for (text, point, fg, bg) in itertools.izip_longest(
                   texts, points, foregrounds, backgrounds):
               if text is not None:
                   string = text
               if fg is not None:
                   self.SetTextForeground(fg)
               if bg is not None:
                   self.SetTextBackground(bg)
               self.DrawText(string, point[0], point[1])
           """)
