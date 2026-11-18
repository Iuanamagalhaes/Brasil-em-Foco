from . import ibge, inpe, openmeteo, infodengue, arquivos

def main(a):
    if not a:
        print(__doc__); return
    f = a[0]
    if f in ("ibge", "tudo"): ibge.run()
    if f == "inpe" or f == "tudo": inpe.run(rapido="--rapido" in a)
    if f in ("openmeteo", "tudo"): openmeteo.run()
    if f in ("infodengue", "tudo"): infodengue.run()
    if f == "atlas": arquivos.run_atlas(a[1])
    if f == "ips": arquivos.run_ips(a[1])

main(sys.argv[1:])
