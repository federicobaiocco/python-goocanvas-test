#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  test_goocanvas.py
#  
#  Copyright 2019 Unknown <root@hp425>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  


import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GooCanvas', '2.0')
from gi.repository import Gtk, Gdk, GooCanvas

import configparser
import os.path as osp
import pdb

# Declaraciones para la configuracion
CONFIGFILE    = "~/.config/test_goocanvas.ini"
DEFAULTCONFIG = """
[tools]
stroke_color_rgba = {}
fill_color_rgba = {}
line_width = {}
""".format(0x00ff00ff, 0xffff00ff, 1.7)


HANDLE_SIZE   = 12
HANDLE_FILL   = 0xffff0080
HANDLE_STROKE = 0x000000ff
BOX_STROKE    = 0x000000ff

def rgba2int(rgba):
    """ Convierte del formato Gdk.RGBA (usado en el seleccionador de colores)
        al format rgba de GooCanvas
    """
    r = int(rgba.red   * 255)
    g = int(rgba.green * 255)
    b = int(rgba.blue  * 255)
    a = int(rgba.alpha * 255)
    return (r * 0x1000000 +
            g * 0x10000 +
            b * 0x100 +
            a)
       
       
def hex2RGBA(rgba_hex):
    """ Convierte de rgba (GooCanvas) a Gdk.RGBA. Utiliza una rutina
        de Gdk.RGBA para 'parsear' un string
    """
    RGBA = Gdk.RGBA()
    rgba = int(rgba_hex)
    RGBA.parse("rgba({},{},{},{})".format(
                 rgba // 0x1000000,
                (rgba // 0x10000) % 256,
                (rgba // 0x100) % 256,
                (rgba % 256) / 255.0))
    return RGBA


class Handle(GooCanvas.CanvasRect):
    """ 'Manijas' para mover y redimensionar objetos en el dibujo.
        La clase provee la posibilidad de especificar un 'handler' para
        avisar al llamador de cambios.
    """
    def __init__(self, layer, x, y, handler = None):
        self.hsize2 = HANDLE_SIZE // 2
        super(Handle, self).__init__(
                    parent = layer,
                    width = HANDLE_SIZE, height = HANDLE_SIZE,
                    fill_color_rgba = HANDLE_FILL,
                    stroke_color_rgba = HANDLE_STROKE,
                    line_width = 1.0)
        self.move_to(x, y)
                    
        self.connect("button-press-event", self.on_button_press)
        self.connect("button-release-event", self.on_button_release)
        self.connect("motion-notify-event", self.on_button_move)

        self.position = None
        self.handler = handler
        
                    
    def on_button_press(self, src, tgt, event):
        """ Cuando se apreta al boton 1, almacenamos la position de este hecho.
        """
        self.position = event.x, event.y
        
        
    def on_button_release(self, src, tgt, event):
        """ Una vez 'soltado' al boton, deshabilitamos self.position.
        """
        self.position = None
        
        
    def on_button_move(self, src, tgt, event):
        """ Movimientos del 'handle' se producen cuando el boton 1 es apretado,
        """
        if self.position != None:
            newpos = event.x, event.y
            dx = newpos[0] - self.position[0]
            dy = newpos[1] - self.position[1]
            
            actual = self.get_position()
            x, y = actual[0] + dx, actual[1] + dy
            
            self.move_to(x, y)
            self.position = x, y
            if self.handler != None:
                self.handler(self.get_position())
        
                    
    def move_to(self, x, y = 0):
        """ Mover el _centro_ del marcador a la posicion x, y
        """
        if isinstance(x, tuple):
            self.set_property('x', x[0] - self.hsize2)
            self.set_property('y', x[1] - self.hsize2)
        else:
            self.set_property('x', x - self.hsize2)
            self.set_property('y', y - self.hsize2)
        
        
    def get_position(self):
        """ Acceso a la posición actual del centro del marcador
            Retorna una tupla con (x, y)
        """
        return (self.get_property('x') + self.hsize2, 
                self.get_property('y') + self.hsize2)
        


class Rectangle():
    """ Contenedor que determina los limites de un objeto a editar.
        En modo normal, las cuatro manijas redimensionan.
    """
    def __init__(self, parent, x, y, width, height):
        self.top_l = (x, y)
        self.btm_r = (x + width, y + height)
        
        self.bbox = GooCanvas.CanvasRect(
                    parent = parent,
                    stroke_color_rgba = BOX_STROKE,
                    line_width = 2.0)
        self.update_properties()

        self.move_handle = Handle(parent,
                    x, y,
                    self.move_handle_callback)
                    
        self.resize_handle = Handle(parent,
                    x + width, y + height,
                    self.resize_handle_callback)


    def update_properties(self):
        new_width  = max(self.btm_r[0] - self.top_l[0], 0)
        new_height = max(self.btm_r[1] - self.top_l[1], 0)
        
        self.bbox.set_property('x', self.top_l[0])
        self.bbox.set_property('y', self.top_l[1])
        self.bbox.set_property('width',  new_width)
        self.bbox.set_property('height', new_height)
        
        
    def set_stroke_rgba(self, rgba):
        self.bbox.set_property("stroke-color-rgba", rgba)
        
        
    def set_fill_rgba(self, rgba):
        self.bbox.set_property("fill-color-rgba", rgba)
        

    def set_line_width(self, width):
        print("width", width)
        self.bbox.set_property("line-width", width)

        
    def move_handle_callback(self, newpos):
        """ El handle superior izq es para mover el bounding box completamente
        """
        # Ya que 'move' no cambia ancho o alto, solo actualizamos top_l
        dist = (newpos[0] - self.top_l[0], newpos[1] - self.top_l[1])
        self.top_l = newpos
        self.btm_r = (self.btm_r[0] + dist[0],
                      self.btm_r[1] + dist[1])
        self.update_properties()

        self.resize_handle.move_to(self.btm_r)


    def resize_handle_callback(self, newpos):
        """ El handle inferior derecha es para redimensionar al bounding box
        """
        # self.top_l   no cambia
        self.btm_r = newpos
        self.update_properties()

class Clear():
    
    def __init__(self, parent):
        
        self.clearBox = GooCanvas.CanvasRect(
                    parent = parent, fill_color = 'white', width = 500, height= 1000)      

        
class Configuration(configparser.ConfigParser):
    """ Maneja la configuracion del programa.
        Inicio del programa: Se leen los valores guardados y se aplican
                a los widgets de dibujo: rellenos, trazo, y ancho
        Al cerrar el program con 'X', se guarda la configuracion
    """
    def __init__(self, confname):
        """ Constructor intenta de leer el archivo de configuracion con nombre
            especificado arriba. Si no existe, leer una configuracion por
            defecto (tambien definido arriba.
        """
        super(Configuration, self).__init__()
        self.confname = osp.expanduser(confname)
        print(confname)

        if osp.exists(self.confname):
            self.read(self.confname)
        else:
            self.read_string(DEFAULTCONFIG)

        self.dump()


    def dump(self):
        """ Mostrar los valores en la configuracion - solo para debugging
        """
        for key in self['tools']:
            val = self['tools'][key]
            print("{:>20s} = {}".format(key, val))
        
        
    def save(self):
        """ Escribir la configuracion al archivo confname)
        """
        with open(self.confname, "w") as conff:
            self.write(conff)
        
class spline():
    def __init__(self, parent, data, x, y, width, height):
        self.top_l = (x, y)
        self.btm_r = (x + width, y + height)
    
        self.bezier = GooCanvas.CanvasPath(
                                    parent = parent,
                                    data = data, 
                                    stroke_color_rgba = BOX_STROKE)
                                    

        self.move_handle = Handle(parent,
                    x, y,
                    self.move_handle_callback)
                    
        self.resize_handle = Handle(parent,
                    x + width, y + height,
                    self.resize_handle_callback)
        
        
    def move_handle_callback(self, newpos):
        """ El handle superior izq es para mover el bounding box completamente
        """
        # Ya que 'move' no cambia ancho o alto, solo actualizamos top_l
        dist = (newpos[0] - self.top_l[0], newpos[1] - self.top_l[1])
        self.top_l = newpos
        self.btm_r = (self.btm_r[0] + dist[0],
                      self.btm_r[1] + dist[1])
        self.update_properties()

        self.resize_handle.move_to(self.btm_r)


    def resize_handle_callback(self, newpos):
        """ El handle inferior derecha es para redimensionar al bounding box
        """
        # self.top_l   no cambia
        self.btm_r = newpos
        self.update_properties()   

    def set_stroke_rgba(self, rgba):
        self.bezier.set_property("stroke-color-rgba", rgba)    

    def update_properties(self):
        new_width  = max(self.btm_r[0] - self.top_l[0], 0)
        new_height = max(self.btm_r[1] - self.top_l[1], 0)
        
        self.bezier.set_property('x', self.top_l[0])
        self.bezier.set_property('y', self.top_l[1])
        self.bezier.set_property('width',  new_width)
        self.bezier.set_property('height', new_height)
        
class Tools(Gtk.Grid):
    def __init__(self, cvroot, config):
        super(Tools, self).__init__()
        self.cvroot = cvroot
        self.config = config
        
        # Seleccion de colores de relleno
        self.fillcolorbtn = Gtk.ColorButton(
                    tooltip_text = "Color de relleno",
                    use_alpha = True,
                    title = "Color de relleno")

        self.fillcolorbtn.set_rgba(
            hex2RGBA(self.config["tools"]["fill_color_rgba"]))
        self.fillcolorbtn.connect("color-set", self.on_fill_color_changed)

        self.attach(self.fillcolorbtn, 0, 0, 1, 2)
        
        # Seleccion de colores del trazo
        self.linecolorbtn = Gtk.ColorButton(
                    tooltip_text = "Color de trazo",
                    use_alpha = True,
                    title = "Color del trazo")
                    
        self.linecolorbtn.set_rgba(
            hex2RGBA(self.config["tools"]["stroke_color_rgba"]))
        self.linecolorbtn.connect("color-set", self.on_line_color_changed)

        self.attach(self.linecolorbtn, 1, 0, 1, 2)
        
        # Ancho del trazo
        adj = Gtk.Adjustment(
                    value = 1, 
                    lower = 0.1,
                    upper = 20.0, 
                    step_increment = 0.1, 
                    page_increment = 0.5, 
                    page_size = 0)
                    
        self.width_btn = Gtk.SpinButton(
                    adjustment = adj,
                    digits = 1,
                    tooltip_text = "Ancho del trazo")
        self.width_btn.set_value(
            float(self.config["tools"]["line_width"]))
        self.width_btn.connect("value-changed", self.on_width_changed)
        
        #~ adj.set_value(float(config["tools"]["line_width"]))
        self.attach(self.width_btn, 2, 0, 1, 2)
        
        # Seleccion de la figura
        col = 20
        for icon, handler, caption in (
                ("icon_rect.svg",     self.start_rect,     "Rectangle"),
                ("icon_ellipse.svg",  self.start_ellipse,  "Ellipse"),
                ("icon_polyline.svg", self.start_polyline, "Polyline"),
                ("icon_spline.svg",   self.start_spline,   "Dpline"),
                ("icon_triangle.svg", self.start_triangle, "Triangulo"),
                ("icon_text.svg",     self.start_text,     "Text"),
                ("clear.svg",     self.clear,     "Borrar")
        ):
            img = Gtk.Image.new_from_file(icon)
            btn = Gtk.Button(
                        tooltip_text = caption)
            btn.set_image(img)
            btn.connect("clicked", handler)
            self.attach(btn, col, 0, 1, 2)
            col += 1

            
    def on_width_changed(self, spbtn):
        """ Handler se llama cuando cambia el ancho del trazo
        """
        width = spbtn.get_value()
        spbtn.set_value(width)
        self.config["tools"]["line_width"] = str(width)


    def on_line_color_changed(self, colorbtn):
        """ Handler se llama cuando cambia el color del trazo
        """
        rgba = colorbtn.get_rgba()
        self.config["tools"]["stroke_color_rgba"] = str(rgba2int(rgba))

        
    def on_fill_color_changed(self, colorbtn):
        """ Handler se llama cuando cambia el color del relleno
        """
        rgba = colorbtn.get_rgba()
        self.config["tools"]["fill_color_rgba"] = str(rgba2int(rgba))

        
    def start_rect(self, btn):
        rect = Rectangle(self.cvroot, 100, 100, 100, 100)
        stroke_color = rgba2int(self.linecolorbtn.get_rgba())
        fill_color   = rgba2int(self.fillcolorbtn.get_rgba())
        line_width   = float(self.width_btn.get_value())
        rect.set_stroke_rgba(stroke_color)
        rect.set_fill_rgba(fill_color)
        rect.set_line_width(line_width)


    def start_ellipse(self):
        pass


    def start_polyline(self):
        pass


    def start_spline(self, btn):
        bezier = spline(
                        self.cvroot,
                        data = "M100,300 C50,160 440,300 340,50",
                        x= 100,
                        y=50,
                        width=240,
                        height= 250)
        stroke_color = rgba2int(self.linecolorbtn.get_rgba())
        bezier.set_stroke_rgba(stroke_color)

    def clear(self, btn):
        clear = Clear(self.cvroot)


    def start_triangle(self):
        pass


    def start_text(self):
        pass

        

class MainWindow(Gtk.Window):
    def __init__(self, config):
        self.config = config

        super(MainWindow, self).__init__()
        self.connect("destroy", self.do_quit)

        
        canvas = GooCanvas.Canvas()
        canvas.set_size_request(400, 500)
        cvroot = canvas.get_root_item()

        # Instanciamos la barra de herramientas
        tools = Tools(cvroot, self.config)

        # Agregamos las barras desplazadoras alrededor del dibujo
        scroller = Gtk.ScrolledWindow()
        scroller.set_size_request(500, 500)
        scroller.add(canvas)
        
        grid = Gtk.Grid()
        grid.attach(scroller, 0, 1, 1, 1)
        grid.attach(tools,    0, 0, 1, 1)
        
        self.add(grid)
        self.show_all()


    def run(self):
        Gtk.main()


    def do_quit(self, btn):
        """ Antes de efectivamente cerrar al lazo principal, guardamos la
            configuracion.
        """
        self.config.save()
        Gtk.main_quit()
        return True



def main(args):
    """ Leemos el archivo de configuracion antes de crear la ventana principal,
        por si queremos almacenar caracteristicas de la misma ventana (por
        ejemplo tamano etc.
    """
    config = Configuration(CONFIGFILE)
    
    mainwdw = MainWindow(config)
    mainwdw.run()

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
