"""Gera os arquivos do media kit da Vibe Eletronics (logos, artes, prévias, zips e PDF).

Uso:  python fontes/gerar.py          (a partir da pasta "Media Kit")
      python fontes/gerar.py pdf      (só refaz o PDF da página)

Precisa do Microsoft Edge e do Pillow. Os flyers vêm de
../Documentos/Vibe Eletronics/Flyer/Novo (rode o exportar.py de lá antes, se mudou algo).
"""
import pathlib
import shutil
import subprocess
import sys
import zipfile

from PIL import Image

FONTES = pathlib.Path(__file__).resolve().parent
KIT = FONTES.parent
IMG = KIT / "img"
DL = KIT / "downloads"
FLYER = KIT.parent / "Documentos" / "Vibe Eletronics" / "Flyer" / "Novo"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def edge(*args: str) -> None:
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", *args],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def foto(pagina: str, saida: pathlib.Path, w: int, h: int, transparente: bool = False) -> Image.Image:
    """Tira uma captura de fontes/<pagina> (com #variação) no tamanho w x h."""
    saida.parent.mkdir(parents=True, exist_ok=True)
    nome, _, variacao = pagina.partition("#")
    url = (FONTES / nome).as_uri() + (f"#{variacao}" if variacao else "")
    extras = ["--default-background-color=00000000"] if transparente else []
    edge(f"--window-size={w},{h}", "--force-device-scale-factor=1",
         "--virtual-time-budget=8000", *extras, f"--screenshot={saida}", url)
    img = Image.open(saida)
    assert img.size == (w, h), f"{saida.name}: tamanho inesperado {img.size}"
    return img


def logo(variacao: str, nome: str, w: int = 2200, h: int = 1500, margem: int = 0) -> None:
    """Captura um logo com fundo transparente e corta nas bordas do desenho."""
    saida = DL / "logos" / nome
    img = foto(f"logo.html#{variacao}", saida, w, h, transparente=True).convert("RGBA")
    caixa = img.getchannel("A").getbbox()
    assert caixa, f"{nome}: saiu vazio (fundo transparente não funcionou?)"
    assert img.getpixel((0, 0))[3] == 0, f"{nome}: o fundo não ficou transparente"
    x0, y0, x1, y1 = caixa
    img.crop((x0 - margem, y0 - margem, x1 + margem, y1 + margem)).save(saida)
    previa(saida, 900)


def previa(origem: pathlib.Path, largura: int, nome: str | None = None) -> None:
    """Versão leve (WebP) para mostrar na página."""
    img = Image.open(origem)
    img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
    if img.width > largura:
        img = img.resize((largura, round(img.height * largura / img.width)), Image.LANCZOS)
    IMG.mkdir(exist_ok=True)
    img.save(IMG / f"{nome or origem.stem}.webp", quality=86, method=6)


def zipar(saida: pathlib.Path, arquivos: list[pathlib.Path], compactar: bool = True) -> None:
    modo = zipfile.ZIP_DEFLATED if compactar else zipfile.ZIP_STORED
    with zipfile.ZipFile(saida, "w", modo) as z:
        for a in arquivos:
            z.write(a, a.name)


def gerar_logos() -> None:
    logo("horizontal-escuro", "vibe-logo-horizontal-fundo-escuro.png")
    logo("horizontal-claro", "vibe-logo-horizontal-fundo-claro.png")
    logo("vertical-escuro", "vibe-logo-vertical-fundo-escuro.png")
    logo("vertical-claro", "vibe-logo-vertical-fundo-claro.png")
    logo("nome-escuro", "vibe-nome-fundo-escuro.png")
    logo("nome-claro", "vibe-nome-fundo-claro.png")
    logo("nome-branco", "vibe-nome-branco.png")
    logo("simbolo", "vibe-simbolo.png")
    zipar(DL / "logos" / "vibe-logos.zip", sorted((DL / "logos").glob("*.png")))


def gerar_redes() -> None:
    redes = DL / "redes"
    foto("social.html#post", redes / "vibe-post-1080.png", 1080, 1080)
    foto("social.html#story", redes / "vibe-story-1080x1920.png", 1080, 1920)
    Image.open(FONTES / "simbolo-original.png").convert("RGB").resize((1080, 1080), Image.LANCZOS) \
        .save(redes / "vibe-avatar-1080.png")
    shutil.copy(FONTES / "qr-instagram.png", redes / "vibe-qr-instagram.png")
    previa(redes / "vibe-post-1080.png", 720)
    previa(redes / "vibe-story-1080x1920.png", 540)
    previa(redes / "vibe-avatar-1080.png", 360)
    previa(redes / "vibe-qr-instagram.png", 360)
    # capa que aparece ao compartilhar o link + ícone da aba
    og = foto("social.html#og", IMG / "og.png", 1200, 630).convert("RGB")
    og.save(IMG / "og.jpg", quality=88)
    (IMG / "og.png").unlink()
    Image.open(DL / "logos" / "vibe-simbolo.png").resize((192, 192), Image.LANCZOS).save(IMG / "icone.png")


def gerar_flyer() -> None:
    destino = DL / "flyer"
    destino.mkdir(parents=True, exist_ok=True)
    for rel in ("Flyer-frente.png", "Flyer-verso.png", "Flyer-Vibe-10x15cm.pdf",
                "grafica/Flyer-Vibe-grafica-com-sangria.pdf",
                "grafica/CMYK/Flyer-Vibe-CMYK-com-sangria.pdf"):
        shutil.copy(FLYER / rel, destino / pathlib.Path(rel).name)
    zipar(destino / "Flyer-Vibe-CMYK-TIFF.zip",
          sorted((FLYER / "grafica" / "CMYK").glob("*-CMYK-sangria.tif")), compactar=False)
    previa(destino / "Flyer-frente.png", 700)
    previa(destino / "Flyer-verso.png", 700)


def gerar_pdf() -> None:
    """Imprime a própria página em PDF (usa o CSS de impressão do index.html)."""
    saida = KIT / "Vibe-Eletronics-Media-Kit.pdf"
    edge("--no-pdf-header-footer", "--virtual-time-budget=10000",
         f"--print-to-pdf={saida}", (KIT / "index.html").as_uri())
    assert saida.stat().st_size > 50_000, "PDF saiu vazio"


if __name__ == "__main__":
    if sys.argv[1:] != ["pdf"]:
        gerar_logos()
        gerar_redes()
        gerar_flyer()
    if (KIT / "index.html").exists():
        gerar_pdf()
    for p in sorted(KIT.rglob("*")):
        if p.is_file() and ".git" not in p.parts and p.suffix in {".png", ".pdf", ".zip", ".webp", ".jpg"}:
            print(f"{p.stat().st_size / 1e6:7.2f} MB  {p.relative_to(KIT)}")
