.subckt nand x y out
Mp1 out x vdd vdd P W =Wp L= Lmin PD = 'Wp + 6*Lmin'
+ PS='Wp + 6*Lmin'
+ AD='3*Wp*Lmin' AS='3*Wp*Lmin'
Mp2 out y vdd vdd P W=Wp L=Lmin
+ PD='Wp + 6*Lmin' PS='Wp + 6*Lmin'
+ AD='3*Wp*Lmin' AS='3*Wp*Lmin'
Mn1 out x node1 0 N W=Wn L=Lmin
+ PD='Wn + 6*Lmin' PS='Lmin'
+ AD='3*Wn*Lmin' AS='Wn*Lmin'
Mn2 node1 y 0 0 N W=Wn L=Lmin
+ PD='Wn + 6*Lmin' PS='Wn + 6*Lmin'
+ AD='3*Wn*Lmin' AS='3*Wn*Lmin'
.ends

* Test de modelo Hspice
.MODEL MODN2 NMOS LEVEL=49
+MOBMOD =1.2 CAPMOD=1.80e+00
+NLEV   =0.0 NOIMOD = 2.9