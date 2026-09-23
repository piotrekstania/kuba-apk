@echo off
rem Uruchamia Generator operatow. Wymaga zainstalowanego Pythona 3.11+.
cd /d "%~dp0"

if not exist .venv (
  echo Pierwsze uruchomienie - przygotowuje srodowisko, to potrwa chwile...
  py -3 -m venv .venv
  if errorlevel 1 python -m venv .venv
  if not exist .venv\Scripts\python.exe (
    echo.
    echo Nie znaleziono Pythona. Zainstaluj go ze strony python.org
    echo i zaznacz opcje "Add Python to PATH", potem uruchom start.bat ponownie.
    pause
    exit /b 1
  )
)

rem Aktualizacja idzie PRZED instalacja bibliotek: gdy nowa wersja dokladana
rem nowa zaleznosc, doinstaluje sie od razu przy tym samym uruchomieniu.
rem Aktualizator stoi na samej bibliotece standardowej, wiec dziala tez wtedy,
rem gdy .venv jest jeszcze pusty. Brak internetu = program startuje po staremu.
.venv\Scripts\python -m app.aktualizacja

rem UWAGA: wszystko powyzej, do wiersza z aktualizacja wlacznie, musi zostac
rem bajt w bajt takie samo. cmd czyta ten plik linijka po linijce i pamieta
rem tylko, na ktorym bajcie skonczyl - a aktualizacja wyzej potrafi podmienic
rem ten plik w trakcie. Po podmianie cmd czyta dalej od tego samego bajtu, juz
rem w nowym pliku, wiec nowa reszta musi zaczynac sie dokladnie tutaj.
rem Pilnuje tego test_uruchom.py.
rem
rem Reszta to jeden blok w nawiasach: cmd wczytuje go w calosci, zanim zacznie
rem go wykonywac, i potem do pliku juz nie siega. Dzieki temu nie przeszkadza
rem mu podmiana start.bat przez drugie uruchomienie w czasie pracy programu,
rem a exit na koncu bloku nie pozwala czytac dalej z pliku, ktory mogl sie
rem w tym czasie zmienic. W bloku nie ma komentarzy i nawiasow w tekstach echo -
rem jedno i drugie potrafi rozbic blok.
rem
rem Biblioteki instalujemy takze wtedy, gdy requirements.txt zmienil sie
rem po ostatniej instalacji - inaczej program dziala ze starymi wersjami.
rem Nieudana instalacja (w terenie nie ma internetu) nie zatrzymuje startu:
rem program rusza z tym, co juz jest, a bez znacznika zainstalowane.txt
rem instalacja dokonczy sie przy nastepnym uruchomieniu z internetem.
rem Gdyby czegos naprawde brakowalo, powie o tym po polsku uruchom.py.
rem
rem Plik .bat nie ma wlasnej ikony - Windows rysuje mu systemowa ikonke wiersza
rem polecen i nie da sie tego zmienic z jego wnetrza. Ikone niesie dopiero skrot,
rem wiec zakladamy go raz, obok programu. Uruchamiany z niego program pokazuje
rem nasz znak na pasku zadan i w oknie konsoli. Skrot mozna przeciagnac na pulpit
rem albo przypiac do paska zadan.
rem Nazwa bez polskich znakow celowo: pliki .bat czytaja sie w stronie kodowej
rem konsoli i "o" z kreska potrafi zamienic sie w krzaka razem z cala linia.
(
  fc /b requirements.txt .venv\zainstalowane.txt >nul 2>&1
  if errorlevel 1 (
    echo Instaluje biblioteki...
    .venv\Scripts\python -m pip install --upgrade pip >nul 2>&1
    .venv\Scripts\python -m pip install -r requirements.txt
    if errorlevel 1 (
      echo.
      echo Nie udalo sie doinstalowac bibliotek - pewnie nie ma internetu.
      echo Uruchamiam program z tymi, ktore juz sa. Instalacja dokonczy sie sama
      echo przy nastepnym uruchomieniu z internetem.
      echo.
    ) else (
      copy /y requirements.txt .venv\zainstalowane.txt >nul
    )
  )
  if not exist "Generator operatow.lnk" powershell -NoProfile -ExecutionPolicy Bypass -Command "$k=(Get-Location).Path; $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $k 'Generator operatow.lnk')); $s.TargetPath=(Join-Path $k 'start.bat'); $s.WorkingDirectory=$k; $s.IconLocation=(Join-Path $k 'app\web\static\logo.ico'); $s.Description='Generator operatow'; $s.Save()" >nul 2>&1
  .venv\Scripts\python uruchom.py
  pause
  exit /b
)
