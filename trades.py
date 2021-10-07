"""
@author: Carlos Andrés Gutiérrez González
"""
# Se impoartan todas la librerias a utilizar
# Librerias para GUI
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import QtWidgets
from PyQt5.QtCore import *
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtGui
from PyQt5.uic import loadUiType

# Librerias para el manejo de datos
import pandas as pd
import numpy as np
import sqlite3

# Libreria para el manejo de fechas
import datetime as dt

# Libreria para el manejo de API's
import requests

#Librerias para el manejo de rutas.
import os
from os import path
import sys 

# Función para el manejo de rutas al momento de ejecución del programa.
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for Py Installer"""
    base_path= getattr(sys,'MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

#Se define y se carga el form que se utilizará.
FORM_CLASS,_=loadUiType(resource_path("trades.ui"))

#Se define la clase Main
class Main(QMainWindow, FORM_CLASS):
      
    
    #Se indican todos los métodos a correrse con el inicio de la aplicación.
    def __init__(self,parent=None):
        super(Main,self).__init__(parent)
        QMainWindow.__init__(self)
        self.setupUi(self)
        self.Get_Data_Active_Trades()
        self.Get_Data_Historic_Trades()
        self.Handel_Buttons()
        self.load_add_trade()
             
    #Se definen los métodos enlazados a un botón.    
    def Handel_Buttons(self):
        self.btn_update.clicked.connect(self.update_price)
        self.btn_end_trade.clicked.connect(self.end_trade)
        self.btn_add_trade.clicked.connect(self.add_trade)
        self.btn_salir.clicked.connect(self.exit)
        self.btn_patch_notes.clicked.connect(self.patch_notes)
        
    #Función para el manejo de las bases de datos.    
    def sql(self,db,query,data):
        
        #Se establece la conexión con la base de datos.
        con=sqlite3.connect(resource_path(db))
        
        #Se crea el cursor para la consulta.
        c=con.cursor()
        
        #Se procede a intentar ejecutar la consulta
        try:
            c.execute(query,data)
        except:
            #La consulta fracasó y se termina la conexion con la base de datos
            con.commit()
            c.close()
            QMessageBox.question(self, 'Advertecia', "Hubo un error al acceder a la base de datos", QMessageBox.Ok)
            return
            
        finally:
            #La consulta fue exitosa y se termina la conexion con la base de datos.
            con.commit()
            c.close()
            return 
           
    #Función para agregar trades.
    def add_trade(self):
        
        #Se guardan todas las variables a utilizar.
        entry_date=self.date_entry_date.date().toPyDate()
        entry_date=entry_date.strftime("%d/%m/%Y")
        symbol=self.txt_symbol.text()
        
        try:
            entry_price=float(self.txt_entry_price.text())
        except:       
            QMessageBox.question(self, 'Advertecia', "El campo Entry Price o puede estar vacio", QMessageBox.Ok)
            return            
            
        try:
            position_size=float(self.txt_position_size.text())
        except:
            QMessageBox.question(self, 'Advertecia', "El campo Position Size o puede estar vacio", QMessageBox.Ok)
            return
        
        try:
            stop_loss=float(self.txt_stop_loss.text())
        except:
            stop_loss=0
            
        try:
            take_profit=float(self.txt_take_profit.text())
        except:
            take_profit=0
            
        current_price=0 
        
        direction=self.cmb_direction.currentText()
        
        #Se realizan la validación del símbolo.
        if symbol.find("/")==-1:
            QMessageBox.question(self, 'Advertecia', "Falta agregar / en el símbolo", QMessageBox.Ok)
            return
        symbol=symbol.upper()
        
        #Se establecen los parametros para ejecutar la consulta SQL.
        query='''INSERT INTO active_trades(entry_date, symbol, direction, entry_price, position_size, stop_loss, take_profit, current_price) VALUES (?,?,?,?,?,?,?,?)'''
        data=(entry_date, symbol, direction, entry_price, position_size, stop_loss, take_profit, current_price)
        self.sql("trades.db",query,data)
               
        #Se reestablecen los textboxes para que esten vacios despues de la carga.
        self.txt_entry_price.setText("")
        self.txt_position_size.setText("")
        self.txt_symbol.setText("")
        self.txt_take_profit.setText("")
        self.txt_stop_loss.setText("")
        
        #Se informa que el trade se ha agregado con éxito y se carga en los active trades.
        self.Get_Data_Active_Trades()
        
        #Se actualizan todos los precios
        self.update_price()
        
        #Se manda mensaje de que la carga concluyó correctamente
        QMessageBox.question(self, 'Advertecia', "El trade se ha agregado con éxito", QMessageBox.Ok)
    
    # Se establecen los parametros iniciales de add trades
    def load_add_trade(self):
        
        # Se establece la fecha del dia de hoy.
        today=dt.date.today()
        self.date_entry_date.setDate(today)
        
        #Se precargan valores en el combobox.
        self.cmb_direction.addItems(["Long","Short"])
        self.cmb_direction.setFixedWidth(167)
        
        #Modifica los textboxes para que solo admiten caracteres numericos.
        self.txt_entry_price.setValidator(QtGui.QDoubleValidator())
        self.txt_position_size.setValidator(QtGui.QDoubleValidator())
        self.txt_stop_loss.setValidator(QtGui.QDoubleValidator())
        self.txt_take_profit.setValidator(QtGui.QDoubleValidator())        
        
    #Funcion para guardar los registros de las conexiones con Binance.
    def Save_Requests(self,status_code):
        #Se guarada el momento en el que se realizo la consulta
        datetime=str(dt.datetime.now())
        
        #Se establecen los parametros para ejecutar la consulta SQL.
        query='''INSERT INTO requests(request_status, date) VALUES (?,?)'''
        data=(status_code,datetime)
        self.sql("trades.db", query, data)
          
    #Función para recalcular despues de actualizar el precio de un trade
    def recalc(self):
        
        #Se cuentan cuantas filas se tienen.
        filas=self.tbl_active_trades.rowCount()

        #Se actualizan los campos necesarios en todas las filas.        
        for a in range(filas):
            
            # Se actualizan los campos PnL y PnLp dependiendo de la dirección.            
            if (self.tbl_active_trades.item(a,3).text())=="Long":
               PnL=float(self.tbl_active_trades.item(a,5).text())*float(self.tbl_active_trades.item(a,9).text())-float(self.tbl_active_trades.item(a,6).text())-float(self.tbl_active_trades.item(a,10).text())
               PnLp=(((float(self.tbl_active_trades.item(a,9).text())/float(self.tbl_active_trades.item(a,4).text())-1)*100))  
            else:
               PnL=float(self.tbl_active_trades.item(a,6).text())-float(self.tbl_active_trades.item(a,5).text())*float(self.tbl_active_trades.item(a,9).text())-float(self.tbl_active_trades.item(a,10).text())
               PnLp=((1-(float(self.tbl_active_trades.item(a,9).text())/float(self.tbl_active_trades.item(a,4).text())))*100)
            
            #Se redondean a dos dígitos los valores obtenidos.                
            PnL=round(PnL,2)
            PnLp=round(PnLp,2)
            
            #Se introducen los campos calculados a la tabla.
            self.tbl_active_trades.setItem(a,11, QTableWidgetItem(str(PnL)))
            self.tbl_active_trades.setItem(a,12, QTableWidgetItem(str(PnLp)))
            
        # Se llama a la función para dar formato a la tabla.    
        filas=self.tbl_active_trades.rowCount()
        columnas=self.tbl_active_trades.columnCount()
        self.table_format(filas,columnas)    

    #Función para hacer los requests del precio actual a Binance    
    def API_Binance_Update_Price(self,symbol):

        #Se establece la conexion con la API de Binance
        current_price=requests.get("http://binance.com/api/v3/ticker/price",params=symbol)
        
        #Se evaluan todos los posibles resultados de la consulta a Binance.
        if current_price.status_code==400:
            self.Save_Requests(current_price.status_code)
            return "Se ha hecho una mala consulta"
        
        if current_price.status_code==403:
            self.Save_Requests(current_price.status_code)
            return "Se ha violado el Firewall"
        
        if current_price.status_code==429:
            self.Save_Requests(current_price.status_code)
            return "Se ha excedido el numero de consultas"
            
        if current_price.status_code==418:
            self.Save_Requests(current_price.status_code)
            return "Se ha bloqueado la dirección IP"
        
        if current_price.status_code>=500:
            self.Save_Requests(current_price.status_code)
            return "Binance esta teniendo problemas"
        
        if current_price.status_code==200:
            try:
                self.Save_Requests(current_price.status_code)                
                return float(current_price.json()["price"])
            except:
                return"Ha ocurrido un error al momento de regresar el precio"    
            
    #Función para la carga inicial de active trades y se le da formato.
    def Get_Data_Active_Trades(self):

        #Se establece la conexión con la base de datos.
        con=sqlite3.connect(resource_path("trades.db"))
        result=pd.read_sql('select * from active_trades',con)
        con.close()
        
        # A partir de la consulta, se crean las columnas necesarias.
        # Se crea la columna Notional Value
        notional_value=pd.DataFrame({'notional_value':(result["entry_price"]*result["position_size"]).round(4)})
        result=pd.concat([result,notional_value],axis=1)
        
        #Se crea la columna de Fees
        fees=pd.DataFrame({'fees':((result['notional_value']*.001)*2).round(4)})
        result=pd.concat([result,fees],axis=1)
        
        #Se crea la columna de PnL dependiendo de la dirección direccion del trade y si tiene o no decimales.
        #Long
        try:
            PnL_Long= ((result["position_size"]*result["current_price"])-result["notional_value"]-result["fees"]).round(2)
        except: 
            PnL_Long= ((result["position_size"]*result["current_price"])-result["notional_value"]-result["fees"])
        
        #Short
        try:
            PnL_Short= (result["notional_value"]-(result["position_size"]*result["current_price"])-result["fees"]).round(2)
        except:
            PnL_Short= (result["notional_value"]-(result["position_size"]*result["current_price"])-result["fees"])
                
        result["PnL"]=np.where(result["direction"]=="Long",PnL_Long,PnL_Short)
                
        #Se crea la columna PnL% dependiendo de la dirección del trade y si tiene o no decimales.
        #Long
        try:
            PnLp_Long=(((result["current_price"])-1)*100).round(2)
        except:
            PnLp_Long=(((result["current_price"]/result["entry_price"])-1)*100)
            
        #Short
        try:
            PnLp_Short=((1-(result["current_price"]/result["entry_price"]))*100).round(2)
        
        except:
            PnLp_Short=((1-(result["current_price"]/result["entry_price"]))*100)
        
        result["PnL%"]=np.where(result["direction"]=="Long",PnLp_Long,PnLp_Short)   
   
        #Acomoda el dataframe en el orden necesario.
        result=result.reindex(columns=["trade_id", "entry_date", "symbol", "direction", "entry_price", "position_size", "notional_value",
                                       "stop_loss", "take_profit", "current_price", "fees", "PnL", "PnL%"])
    
        #Establece el tamaño del DataFrame a cargar.
        shape=result.shape
        filas=shape[0]
        columnas=shape[1]
    
        #Carga en la tabla los datos obtenidos de la consulta
        self.tbl_active_trades.setRowCount(0)

        for a in range(filas):
            self.tbl_active_trades.insertRow(a)
            for b in range(columnas):
                item=(result.iloc[a,b])
                self.tbl_active_trades.setItem(a,b, QTableWidgetItem(str(item)))
        
        #Se le da formato a la tabla
        self.table_format(filas,columnas)
        
        #Establece el modo solo lectura a la tabla
        self.tbl_active_trades.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        #Se manda llamar a la función para generar el resumen de todos los trades.
        self.summary_active_trades(filas)

    #Función para dar formato a la tabla de active_trades
    def table_format(self,filas,columnas):
        #Definición De Colores
        fondo_verde=QtGui.QColor(0,176,80)
        texto_verde=QtGui.QColor(0,97,0)
        
        fondo_rojo=QtGui.QColor(255,0,0)
        texto_rojo=QtGui.QColor(156,0,6)
        
        # Colores Rojo/Verde
        for a in range(filas):
            
            #Formato para current_price
            if  float(self.tbl_active_trades.item(a,9).text())> float(self.tbl_active_trades.item(a,4).text()):
                self.tbl_active_trades.item(a,9).setBackground(fondo_verde)
                self.tbl_active_trades.item(a,9).setForeground(texto_verde)
            else:
                self.tbl_active_trades.item(a,9).setBackground(fondo_rojo)
                self.tbl_active_trades.item(a,9).setForeground(texto_rojo)
            
            #Formato para PnL
            if  float(self.tbl_active_trades.item(a,11).text())>0:
                self.tbl_active_trades.item(a,11).setBackground(fondo_verde)
                self.tbl_active_trades.item(a,11).setForeground(texto_verde)
            else:
                self.tbl_active_trades.item(a,11).setBackground(fondo_rojo)
                self.tbl_active_trades.item(a,11).setForeground(texto_rojo)
                
            #Formato para PnL%    
            if  float(self.tbl_active_trades.item(a,12).text())>0:
                self.tbl_active_trades.item(a,12).setBackground(fondo_verde)
                self.tbl_active_trades.item(a,12).setForeground(texto_verde)
            else:
                self.tbl_active_trades.item(a,12).setBackground(fondo_rojo)
                self.tbl_active_trades.item(a,12).setForeground(texto_rojo)

        #Fuente Y Alineación De Columnas
        for a in range(filas):
            for b in range(columnas):
                self.tbl_active_trades.item(a,b).setFont(QtGui.QFont('Arial', 9, QtGui.QFont.Bold))
                self.tbl_active_trades.item(a,b).setTextAlignment(Qt.AlignCenter)
                
        #Column Resize
        self.tbl_active_trades.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.tbl_active_trades.resizeColumnsToContents()
        
        #Header Borders
        self.tbl_active_trades.setStyleSheet( "QHeaderView::section{"
            "border-top:0px solid #D8D8D8;"
            "border-left:0px solid #D8D8D8;"
            "border-right:1px solid #D8D8D8;"
            "border-bottom: 1px solid #D8D8D8;"
            "background-color:white;"
            "padding:4px;"
        "}"
        "QTableCornerButton::section{"
            "border-top:0px solid #D8D8D8;"
            "border-left:0px solid #D8D8D8;"
            "border-right:1px solid #D8D8D8;"
            "border-bottom: 1px solid #D8D8D8;"
            "background-color:white;"
        "}");
              
    #Función para cargar y dar formato a los historic trades.        
    def Get_Data_Historic_Trades(self):
        
        #Se establece la consulta con la tabla
        con=sqlite3.connect(resource_path("trades.db"))
        result=pd.read_sql('select * from historic_trades',con)
        con.close()
        
        #Se determina el tamaño de la consulta realizada
        shape=result.shape
        filas=shape[0]
        columnas=shape[1]
        
        #Carga en la tabla los datos obtenidos de la consulta
        self.tbl_historic_trades.setRowCount(0)

        for a in range(filas):
            self.tbl_historic_trades.insertRow(a)
            for b in range(columnas):
                item=(result.iloc[a,b])
                self.tbl_historic_trades.setItem(a,b, QTableWidgetItem(str(item)))
                
                
        #Establece el formato de la tabla
        #Definición De Colores
        fondo_verde=QtGui.QColor(0,176,80)
        texto_verde=QtGui.QColor(0,97,0)
        
        fondo_rojo=QtGui.QColor(255,0,0)
        texto_rojo=QtGui.QColor(156,0,6)
        
        for a in range(filas):
        
            #Formato para exit price
            if  float(self.tbl_historic_trades.item(a,10).text())> float(self.tbl_historic_trades.item(a,5).text()):
                self.tbl_historic_trades.item(a,10).setBackground(fondo_verde)
                self.tbl_historic_trades.item(a,10).setForeground(texto_verde)
            else:
                self.tbl_historic_trades.item(a,10).setBackground(fondo_rojo)
                self.tbl_historic_trades.item(a,10).setForeground(texto_rojo)
            
            #Formato para PnL
            if  float(self.tbl_historic_trades.item(a,12).text())>0:
                self.tbl_historic_trades.item(a,12).setBackground(fondo_verde)
                self.tbl_historic_trades.item(a,12).setForeground(texto_verde)
            else:
                self.tbl_historic_trades.item(a,12).setBackground(fondo_rojo)
                self.tbl_historic_trades.item(a,12).setForeground(texto_rojo)
                
            #Formato para PnL%    
            if  float(self.tbl_historic_trades.item(a,13).text())>0:
                self.tbl_historic_trades.item(a,13).setBackground(fondo_verde)
                self.tbl_historic_trades.item(a,13).setForeground(texto_verde)
            else:
                self.tbl_historic_trades.item(a,13).setBackground(fondo_rojo)
                self.tbl_historic_trades.item(a,13).setForeground(texto_rojo)
                
            for a in range(filas):
                for b in range(columnas-1):
                    self.tbl_historic_trades.item(a,b).setFont(QtGui.QFont('Arial', 9, QtGui.QFont.Bold))
                    self.tbl_historic_trades.item(a,b).setTextAlignment(Qt.AlignCenter)
                    
            #Column Resize
            self.tbl_historic_trades.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
            self.tbl_historic_trades.resizeColumnsToContents()
            
            #Header Borders
            self.tbl_historic_trades.setStyleSheet( "QHeaderView::section{"
                "border-top:0px solid #D8D8D8;"
                "border-left:0px solid #D8D8D8;"
                "border-right:1px solid #D8D8D8;"
                "border-bottom: 1px solid #D8D8D8;"
                "background-color:white;"
                "padding:4px;"
            "}"
            "QTableCornerButton::section{"
                "border-top:0px solid #D8D8D8;"
                "border-left:0px solid #D8D8D8;"
                "border-right:1px solid #D8D8D8;"
                "border-bottom: 1px solid #D8D8D8;"
                "background-color:white;"
            "}");
      
        #Establece el modo solo lectura en la tabla
        self.tbl_historic_trades.setEditTriggers(QAbstractItemView.NoEditTriggers)
                                                                                      
    #Función para terminar los trades y pasarlos a históricos.    
    def end_trade(self):
        
        #Se recupera la fila del trade que se va a terminar.
        fila=self.tbl_active_trades.currentRow()
        
        #Verifica que se seleccione una fila valida
        if fila<0:
            QMessageBox.question(self, 'Advertecia', "Por favor seleccione una fila", QMessageBox.Ok)
            return
        
        #Se le pregunta al usuario el precio de salida.
        exit_price,okPressed=QInputDialog.getText(self,"Exit Price","Exit Price:", QLineEdit.Normal, "")
        
        #Termina la ejecucucion si se da click en cancelar
        if okPressed==False or exit_price=="":
            return
        
        #Verifica que se hayan introducido solo caracteres numéricos
        try:
            exit_price=float(exit_price)
        except:
            return
        
        #InputBox para introducir la fecha de cierre del trade.
        today=dt.date.today()
        today=today.strftime("%d/%m/%Y")
        exit_date,okPressed2=QInputDialog.getText(self,"Exit Date","Date:", QLineEdit.Normal, today)
        
        #Termina la ejecucion
        if okPressed==False or exit_date=="":
            return
                
        #Se almacenan las variables a grabar en la tabla.
        trade_id= int(self.tbl_active_trades.item(fila,0).text())
        entry_date= self.tbl_active_trades.item(fila,1).text()
        symbol= self.tbl_active_trades.item(fila,2).text()
        direction= self.tbl_active_trades.item(fila,3).text()
        entry_price= float(self.tbl_active_trades.item(fila,4).text())
        position_size= float(self.tbl_active_trades.item(fila,5).text())
        notional_value= float(self.tbl_active_trades.item(fila,6).text())
        try:
            stop_loss= float(self.tbl_active_trades.item(fila,7).text())
        except:
            stop_loss=0
            
        try:    
            take_profit=float(self.tbl_active_trades.item(fila,8).text())
        except:
            take_profit=0
            
        fees=float(self.tbl_active_trades.item(fila,10).text())
        
        if direction=="Long":
            pnl=round(position_size*exit_price)-notional_value-fees
            pnl=round(pnl,2)
        else:
            pnl=(notional_value-(position_size*exit_price)-fees)
            pnl=round(pnl,2)
        
        if direction=="Long":  
            pnlp= (((exit_price/entry_price)-1)*100)
            pnlp=round(pnlp,2)
        else:
            pnlp=((1-(exit_price/entry_price))*100)
            pnlp=round(pnlp,2)
            
        #Se agrega el trade a historic trades
        query='''INSERT INTO historic_trades(trade_id, entry_date, exit_date, symbol, direction, entry_price, position_size,
                 notional_value,stop_loss, take_profit, exit_price, fees, pnl, pnlp) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)'''        
        data=(trade_id, entry_date, exit_date, symbol, direction, entry_price, position_size, notional_value, stop_loss, take_profit, exit_price, fees, pnl, pnlp)
        self.sql("trades.db", query, data)
        
        # Se elimina el renglon de la tabla
        self.tbl_active_trades.removeRow(self.tbl_active_trades.currentRow())
        
        #Se elimina el registro de la tabla active_trades
        con=sqlite3.connect(resource_path("trades.db"))
        c=con.cursor()
        query='''DELETE FROM active_trades WHERE trade_id= ?'''
        data=trade_id
        
        try:
            c.execute(query,(data,))
        except:
            con.commit()
            c.close()
        finally:
            con.commit()
            c.close()
            
        
        #Se actualizan las tablas para mostrar la información.
        self.Get_Data_Active_Trades()
        self.Get_Data_Historic_Trades()

    #Función para cerrar la aplicación con la tecla escape.
    def keyPressEvent(self,event):
                
        if event.key()==Qt.Key_Escape:
            buttonReply=QMessageBox.question(self, 'Salir', "Esta seguro que desea salir de la aplicación", QMessageBox.Yes | QMessageBox.No )
            if buttonReply == QMessageBox.Yes:
                self.close()
            if buttonReply == QMessageBox.No:
                return
    #Función para actualizar el preio con Binance    
    def update_price(self):
          
        symbols=[]
        updated_prices=[]
        
        #Se cuentan cuantos simbolos se actualizar
        filas=self.tbl_active_trades.rowCount()
        
        #Se extraen los simbolos a actualizar y se guardan en una lista.
        for a in range(filas):
             symbol=self.tbl_active_trades.item(a,2).text()
             symbol=symbol.replace("/","")
             symbol="symbol="+symbol
             
             symbols.append(symbol)
        
        #Se pide el precio actualizado a Binance.
        for symbol in symbols:
            updated_prices.append(self.API_Binance_Update_Price(symbol))
             
        #Se actualiza la tabla tbl_active_trades y la base de datos active_trades     
        for a, updated_price in enumerate(updated_prices):
            self.tbl_active_trades.setItem(a,9, QTableWidgetItem(str(updated_price)))

            query="""Update active_trades set current_price= ? where trade_id = ?"""
            trade_id=int(self.tbl_active_trades.item(a,0).text())
            data=(float(updated_price), trade_id)
            self.sql("trades.db", query, data)

        self.recalc()  
        
    #Función para tener las estadisticas del momento actualizadas.   
    def summary_active_trades(self,filas):
        
        #Se definen las variables.
        notional_value=0
        pnl=0
        
        #Se extraen los datos y se suman.
        for a in range (filas):
            notional_value+=float(self.tbl_active_trades.item(a,6).text())
            pnl+=float(self.tbl_active_trades.item(a,11).text())
            
        #Se calcula el pnlp
        if notional_value!=0:
            pnlp=(pnl/notional_value)*100
        
            #Se le da formato a los labels dependiendo de sus condiciones.
            if pnl>0:
                self.lbl_pnl.setStyleSheet("QLabel {color : green;}")
                self.lbl_pnlp.setStyleSheet("QLabel {color: green;}")
    
            if pnl<0:
                self.lbl_pnl.setStyleSheet("QLabel {color : red;}")
                self.lbl_pnlp.setStyleSheet("QLabel {color: red;}")
            
            #Se cargan las variables a sus respectivos labels 
            self.lbl_notional_value.setText(str(notional_value))
            self.lbl_pnl.setText(str(pnl))
            self.lbl_pnlp.setText(str(pnlp))
        
        self.lbl_notional_value.setVisible(False)   
        self.lbl_pnl.setVisible(False)   
        self.lbl_pnlp.setVisible(False)   
   
    def exit(self):
        buttonReply=QMessageBox.question(self, 'Salir', "Esta seguro que desea salir de la aplicación", QMessageBox.Yes | QMessageBox.No )
        if buttonReply == QMessageBox.Yes:
            self.close()
        if buttonReply == QMessageBox.No:
            return
    
    def patch_notes(self):
        os.startfile(resource_path("patch.txt"))

         
        
def main():
    app=QApplication(sys.argv)
    window=Main()
    window.show()
    app.exec()
    
if __name__=='__main__':
    main()


    
###Reserva de codigo###
#geo=self.tbl_active_trades.geometry()
#print(geo)

#Codigo para poner el tooltiptext//se hizo desde el formulario.        
#self.tbl_active_trades.horizontalHeaderItem(0).setToolTip("hola")
#self.tab_trades.currentChanged.connect(self.onChange)
    