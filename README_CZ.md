# astOS (Arch Snapshot Tree OS)
### Neměnná distribuce založená na archi využívající snapshoty btrfs.  

---

## Obsah
* [Co je astOS?](https://github.com/CuBeRJAN/astOS/blob/main/README_CZ.md#co-je-astos)
* [astOS ve srovnání s jinými podobnými distribucemi](https://github.com/CuBeRJAN/astOS/blob/main/README_CZ.md#ast-ve-srovnání-s-jinými-podobnými-distribucemi)
* [dokumentace k ast a astOS](https://github.com/CuBeRJAN/astOS/blob/main/README_CZ.md#dokumentace-k-ast-a-astos)
  * [Instalace](https://github.com/CuBeRJAN/astOS/blob/main/README_CZ.md#instalace)
  * [Po instalaci](https://github.com/CuBeRJAN/astOS/blob/main/README_CZ.md#po-instalaci)
  * [Správa snímků a nasazení](https://github.com/CuBeRJAN/astOS/blob/main/README_CZ.md#správa-snímků)
  * [Správa balíčků](https://github.com/CuBeRJAN/astOS/blob/main/README_CZ.md#správa-balícků)
* [Další dokumentace](https://github.com/CuBeRJAN/astOS/blob/main/README_CZ.md#další-dokumentace)
* [Známé chyby](https://github.com/CuBeRJAN/astOS/blob/main/README_CZ.md#známe-chyby)
* [Přispívání](https://github.com/CuBeRJAN/astOS/blob/main/README_CZ.md#přispívaní)

---

## Co je astOS?  

astOS je moderní distribuce založená na [Arch Linuxu](https://archlinux.org).  
Na rozdíl od Archu používá neměnný (pouze pro čtení) kořenový souborový systém.  
Software je instalován a konfigurován do jednotlivých stromů snímků, které lze následně nasadit a zavést do systému.  
Nepoužívá vlastní formát balíčků ani správce balíčků, místo toho se spoléhá na [pacman](https://wiki.archlinux.org/title/pacman) z Archu.


**To má několik výhod:**

* Bezpečnost
  * I když je aplikace spuštěna s vyvýšenímy právy, nemůže nahradit systémové knihovny škodlivými verzemi.
* Stabilita a spolehlivost
  * Díky tomu, že je systém připojen pouze pro čtení, není možné omylem přepsat systémové soubory.
  * Pokud se systém dostane do problémů, můžete během několika minut snadno vrátit poslední funkční snímek.
  * Atomické aktualizace - aktualizace systému najednou je spolehlivější.
  * Díky funkci snapshotu může systém astOS dodávat špičkový software, aniž by se stal nestabilním
  * astOS nepotřebuje téměř žádnou údržbu, protože má vestavěný plně automatický aktualizační nástroj, který před aktualizacemi vytváří snapshoty a před nasazením nového snapshotu automaticky kontroluje, zda se systém správně aktualizoval
* Konfigurovatelnost
  * Díky snapshotům uspořádaným do stromu můžete mít snadno k dispozici více různých konfigurací softwaru s různými balíčky, aniž by došlo k jakémukoli zásahu do systému
  * Například: můžete mít nainstalovanou jednu pracovní plochu Gnome a nad ní mít dva překryvy - jeden s videohrami, s nejnovějším jádrem a ovladači, a druhý pro práci, s jádrem LTS a stabilnějším softwarem, mezi nimiž pak můžete snadno přepínat podle toho, co se snažíte dělat.
  * Můžete také snadno zkoušet software, aniž byste se museli obávat, že si rozbijete systém nebo ho znečistíte nepotřebnými soubory, například můžete vyzkoušet nové desktopové prostředí ve snapshotu a poté snapshot smazat, aniž byste vůbec měnili svůj hlavní systém.
  * To lze využít i pro víceuživatelské systémy, kde má každý uživatel zcela samostatný systém s jiným softwarem, a přesto může sdílet určité balíčky, například jádra a ovladače.
  * astOS umožňuje instalovat software pomocí chrootování do snapshotů, proto můžete k instalaci dalších balíčků použít software, jako je AUR.
  * astOS je stejně jako Arch velmi přizpůsobitelný, můžete si přesně vybrat software, který chcete používat.

* Díky své spolehlivosti a automatickým aktualizacím je astOS vhodný pro jednorázová nebo vestavěná zařízení.
* Je také dobrou distribucí pro pracovní stanice nebo obecné použití s využitím vývojových kontejnerů a flatpaku pro desktopové aplikace. 

---
## astOS ve srovnání s jinými podobnými distribucemi
* **NixOS** - ve srovnání s nixOS je astOS tradičnější systém, co se týče nastavení a údržby. Zatímco nixOS je kompletně konfigurován pomocí programovacího jazyka Nix, astOS používá správce balíčků Arch pacman. astOS používá snímky btrfs, zatímco NixOS vytváří obrazy systému squashfs.
  * astOS umožňuje deklarativní konfiguraci pomocí Ansible, pro podobnou funkčnost jako NixOS.
* **Fedora Silverblue** - astOS je lépe přizpůsobitelný, ale vyžaduje více ručního nastavení.
* **OpenSUSE MicroOS** - astOS je více přizpůsobitelný systém, ale opět vyžaduje trochu více ručního nastavení. MicroOS funguje podobně jako astOS ve způsobu, jakým využívá snímky btrfs.

---
## Instalace
* astOS se instaluje z oficiálního Live iso Arch Linuxu dostupného na [https://archlinux.org/](https://archlinux.org).

Nejprve nainstalujte git - to nám umožní stáhnout instalační skript.

```
pacman -Sy git
```
Klonování repozitáře

```
git clone "https://github.com/CuBeRJAN/astOS"  
cd astOS  
```
Rozdělení a formátování disku

```
lsblk # Zjistěte název jednotky
cfdisk /dev/*** # naformátujte disk, nezapomeňte přidat oddíl EFI, pokud používáte BIOS, nechte před oddílem 2M pro bootloader  
```
Spusťte instalační program

```
python3 main.py /dev/<oddíl> /dev/<disk> /dev/<efi oddíl> # V případě instalace v režimu BIOS můžete oddíl EFI vynechat.
```

## Nastavení po instalaci
* astOS neprovádí mnoho nastavení pro uživatele, proto bude nutné provést nějaké nastavení po instalaci.
* Mnoho informací o tom, jak zvládnout poinstalační nastavení, je k dispozici na stránce [ArchWiki](https://wiki.archlinux.org/title/general_recommendations). 
* Zde je malý příklad postupu nastavení:
  * Začněte vytvořením nového snímku ze základního obrazu pomocí ```ast clone 0```)
  * Uvnitř tohoto nového snapshotu proveďte chroot (```ast chroot <snapshot>```) a začněte s nastavováním.
    * Začněte přidáním nového uživatelského účtu: ```useradd username```
    * Nastavte uživatelské heslo ```passwd username```
    * Nyní nastavte nové heslo pro uživatele root ```passwd root```
    * Nyní můžete pomocí programu pacman nainstalovat další balíčky (desktopová prostředí, kontejnerové technologie, flatpak).
    * Po dokončení ukončete chroot pomocí ```exit```
    * Poté jej můžete nasadit pomocí ```ast deploy <snapshot>```

## Další dokumentace
* Doporučujeme podívat se na [Arch wiki](https://wiki.archlinux.org/), kde najdete dokumentaci, která není součástí tohoto projektu.
* Nahlášení problémů/chyb na [Github issues page](https://github.com/CuBeRJAN/astOS/issues).

#### Základní obraz
* Snímek ```0``` je vyhrazen pro základní obraz systému, nelze jej měnit a lze jej aktualizovat pouze pomocí ```ast base-update```.

## Správa snímků

#### Zobrazit strom souborového systému

```
ast strom
```

* Výstup může vypadat například takto:

```
root - kořen
├── 0 - základní obraz
└── 1 - víceuživatelský systém
    └── 4 - aplikace
        ├── 6 - plná pracovní plocha MATE
        └── 2*- plná pracovní plocha Plasma
```
* Hvězdička ukazuje, který snímek je aktuálně zvolen jako výchozí

* Můžete také získat pouze číslo aktuálně spuštěného snapshotu pomocí příkazu

```
ast current
```
#### Přidání popisu ke snímku
* Snímky umožňují přidat k nim popis pro snadnější identifikaci.

```
ast desc <snímek> <popis>
```
#### Odstranění stromu
* Odstraní strom a všechny jeho větve.

```
ast del <strom>
```
#### Vlastní konfigurace spouštění
* Pokud potřebujete použít vlastní konfiguraci grubu, chrootněte se do snapshotu a upravte ```/etc/default/grub```, poté snapshot nasaďte a restartujte počítač.

#### chroot do snapshotu 
* Po vstupu do chrootu se operační systém chová jako běžný Arch, takže můžete instalovat a odebírat balíčky pomocí pacmanu nebo podobného nástroje.
* Nespouštějte ast zevnitř chrootu, mohlo by dojít k poškození systému, je zde pojistka proti selhání, kterou lze obejít pomocí ```--chroot```, pokud to opravdu potřebujete (nedoporučuje se).  

```
ast chroot <snapshot>
```

#### Další možnosti chrootu

* Spustí příkaz ve snapshotu

```
ast run <snapshot> <příkaz>
```

* Spustí příkaz ve snapshotu a všech jeho podvětvích

```
ast tree-run <strom> <příkaz>
```


#### Klonování snímku
* Klonuje snapshot jako nový strom.

```
ast clone <snapshot>
```
#### Vytvoří novou větev stromu

* Přidá novou větev k zadanému snímku.

```
ast branch <snapshot, z něhož se má větev vytvořit>
```
#### Klonování snímku pod stejným rodičem

```
ast cbranch <snapshot>
```
#### Klonování snímku pod zadaným rodičem

* Nezapomeňte po této funkci synchronizovat strom
* Rodič je větev pod kterou chcete klonovat

```
ast ubranch <rodič> <snapshot>
```
#### Vytvoření nového základního stromu

```
ast new
```
#### Nasadit snímek  

* Po nasazení restartujte systém, abyste nabootovali do nového snapshotu.

```
ast deploy <snapshot>  
```
#### Aktualizovat základnu, ze které se sestavují nové snapshoty

```
ast base-update
```
* Poznámka: samotná báze je umístěna na ```/.overlays/overlay-0```, přičemž její specifické soubory ```/var``` a ```/etc``` jsou umístěny na ```/.var/var-0``` a ```/.etc/etc-0```, proto pokud opravdu potřebujete provést změnu konfigurace, můžete tyto snapshoty připojit jako read-write a poté snapshoty zpět jako read only

## Správa balíčků

#### Instalace softwaru
* Po instalaci nového softwaru spusťte ```ast deploy <snapshot>``` a restartujte počítač, aby se změny uplatnily.
* Software lze také nainstalovat pomocí pacmanu do chrootu
* Pod chrootem lze použít AUR
* Pro trvalou instalaci balíčků lze použít Flatpak
* Použití kontejnerů pro instalaci dalšího softwaru je také možností, výhodou je, že není třeba restartovat počítač. Doporučeným způsobem je použití [distrobox](https://github.com/89luca89/distrobox).

```
ast install <snapshot> <balíček>
```
* Po instalaci můžete synchronizovat nově nainstalované balíčky do všech větví stromu pomocí příkazu

```
ast sync <strom>
```

#### Odtraňování softwaru

* Pro jediný snapshot

```
ast remove <snapshot> <balíček či balíčky>
```

* Rekurzivně

```
ast tree-rmpkg <strom> <balíček či balíčky>
```




#### Aktualizace
* Před aktualizací se doporučuje klonovat snímek, abyste se mohli v případě selhání vrátit zpět.

* Aktualizace jednoho snímku

```
ast upgrade <snapshot>
```
* Pro rekurzivní aktualizaci celého stromu

```
ast tree-update <strom>
```

* ast podporuje také automatické aktualizace, ty automaticky klonují, pak aktualizují systém a výstupní kód výstupu zapíší do souboru
* Tím se také vytvoří nový snímek pro zpětné vrácení v případě, že aktualizace způsobí problémy.
* Soubor update.py obsahuje jednoduchý skript pro automatickou aktualizaci systému a nasazení v případě úspěchu, můžete přidat skript crontab, který spustí update.py pro automatickou aktualizaci systému
```
ast auto-upgrade
```

* Chcete-li zjistit stav a datum poslední automatické aktualizace, spusťte příkaz

```
ast check
``` 

* Tuto funkci lze nakonfigurovat ve skriptu (tj. ve skriptu crontab) pro snadné a bezpečné automatické aktualizace.

## Známé chyby

* Při spuštění ast bez argumentů - IndexError: index seznamu mimo rozsah
* Při spuštění ast bez práv roota se místo chybové zprávy zobrazí chyba s odepřenými právy.
* GDM a LightDM nemusí fungovat  
* Docker má problémy s oprávněními, pro opravu spusťte

```
sudo chmod 666 /var/run/docker.sock
```
* Pokud narazíte na nějaké problémy, nahlaste je na [stránce problémů](https://github.com/CuBeRJAN/astOS/issues).

# Přispívání
* Příspěvky do kódu a dokumentace jsou vítány
* Dobrým způsobem, jak přispět k projektu, je také hlášení chyb.
* Před odesláním pull requestu kód otestujte a ujistěte se, že je řádně okomentován.

---

**Projekt je licencován pod licencí AGPLv3**
