SimTools – Qt-Designer-Integration
================================

1. Abhaengigkeiten installieren (im VS-Code-Terminal / PowerShell):

   py -m pip install PyQt6 matplotlib numpy

2. Alle Dateien aus diesem Ordner gemeinsam in euer Projekt kopieren.
   (Vorher eure Originaldateien sichern, insbesondere main.py/values.py.)

3. Starten:

   py main.py

4. Das Qt-Designer-Layout steckt in mainwindow.ui. Ihr koennt diese
   Datei jederzeit mit dem Qt Designer weiter bearbeiten. Wichtig:
   die Widgetnamen (z.B. PlayButton, widget, AbwehrDurchfuehrung)
   sollten gleich bleiben.

5. Funktionen:
   - Szenario 'Vorbeiflug' oder 'Kollision' fuer den aktiven Asteroiden
   - Durchmesser/Masse fuer 'Eigener Asteroid' anpassen
     (Masse in Einheiten 10^10 kg, z.B. 1.0 bedeutet 10^10 kg)
   - Geschwindigkeitsrichtung und -staerke einstellen
   - Weitere Asteroiden hinzufuegen und in der Liste auswaehlen
   - Play/Pause, Stop, Zurueck
   - Erde/Asteroid verfolgen; erneuter Klick fuehrt zur Sonnenansicht
   - Abwehrmethode, Impulswinkel und Eingriffszeitpunkt festlegen
   - 'Abwehr durchfuehren' startet einen neuen Durchlauf bei Tag 0

Wichtige Hinweise:
  * Die voreingestellte Kollision von Meteoroid 1 ist auf Tag 80
    kalibriert (ca. 79,96 Tage). Bei anderen Richtungen, Massen,
    Geschwindigkeiten oder zusaetzlichen Asteroiden kann dies abweichen.
  * Die Impulswerte sind frei gewaehlt und nur Modellwerte.
  * Der Impuls wird einmalig auf die Geschwindigkeit addiert.
  * Die Qt-Ansicht ersetzt die alte Matplotlib-Oberflaeche in aniUI.py.
    Die alte Datei wird nicht mehr importiert und kann archiviert werden.
  * Stop pausiert, Zurueck springt zum Anfang.
  * Dies ist eine Modell-Demonstration, kein echtes Abwehrkonzept.

6. Optionaler Physiktest ohne grafische Oberflaeche:

   py test_modell.py

Hinweis zum Teststand: Der Physiktest wurde ausgefuehrt. Ein direkter
Qt-Fenstertest konnte in der Erstellungsumgebung nicht durchgefuehrt
werden, weil PyQt6 dort nicht installiert ist.
