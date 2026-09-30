# -*- coding: utf-8 -*-
"""
upload_ftp.py — push the built board onto trilumi.xyz (Hostinger, Pure-FTPd TLS).

Hostinger shared hosting: the FTP root is the ACCOUNT root, the site lives at
    domains/<domain>/public_html/
so the default remote dir below is right for trilumi.xyz.

Usage
-----
    python upload_ftp.py --user u123456789 --pass 'THEPASSWORD' \
        --domain trilumi.xyz --sub token2049

    # or point anywhere explicitly
    python upload_ftp.py --user u123456789 --pass 'X' --remote domains/trilumi.xyz/public_html/token2049

    # dry run: connect, list, do not write
    python upload_ftp.py --user u123456789 --pass 'X' --dry

Options
-------
    --host     default ftp.<domain>  (falls back to the resolved A record IP)
    --file     local html, default deploy/trilumi/index.html
    --remote   remote directory, default domains/<domain>/public_html/<sub>
    --index    also write it as <sub>/index.html  (default yes)
    --no-tls   plain FTP if the server refuses AUTH TLS
"""
import argparse, ftplib, io, os, socket, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve(domain):
    try:
        return socket.gethostbyname(domain)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--pass", dest="pw", required=True)
    ap.add_argument("--domain", default="trilumi.xyz")
    ap.add_argument("--sub", default="token2049")
    ap.add_argument("--host", default="")
    ap.add_argument("--port", type=int, default=21)
    ap.add_argument("--file", default=os.path.join(BASE, "deploy", "trilumi", "index.html"))
    ap.add_argument("--remote", default="")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--no-tls", action="store_true")
    a = ap.parse_args()

    host = a.host or ("ftp." + a.domain)
    try:
        socket.gethostbyname(host)
    except Exception:
        host = resolve(a.domain) or host
    remote = a.remote or "domains/%s/public_html/%s" % (a.domain, a.sub)

    if not os.path.exists(a.file):
        sys.exit("no such file: %s" % a.file)

    print("host   ", host)
    print("remote ", remote)
    print("file   ", a.file, "(%.0f KB)" % (os.path.getsize(a.file) / 1024))

    ftp = ftplib.FTP_TLS(timeout=30) if not a.no_tls else ftplib.FTP(timeout=30)
    ftp.connect(host, a.port)
    ftp.login(a.user, a.pw)
    if not a.no_tls:
        try:
            ftp.prot_p()
        except Exception as e:
            print("WARN: prot_p failed (%s) — data channel not encrypted" % e)
    print("login ok —", ftp.getwelcome().strip()[:70])

    # walk / create the remote directory chain
    def cd_or_mkdir(path):
        parts = [p for p in path.strip("/").split("/") if p]
        for p in parts:
            try:
                ftp.cwd(p)
            except Exception:
                print("  mkdir", p)
                if not a.dry:
                    ftp.mkd(p)
                ftp.cwd(p)

    home = ftp.pwd()
    cd_or_mkdir(remote)
    print("cwd    ", ftp.pwd())

    if a.dry:
        print("\n--dry: not writing. remote listing:")
        ftp.retrlines("LIST")
        ftp.quit()
        return

    with open(a.file, "rb") as fh:
        buf = io.BytesIO(fh.read())
    buf.seek(0)
    ftp.storbinary("STOR index.html", buf)
    print("uploaded ->", ftp.pwd() + "/index.html")
    ftp.quit()

    url = "https://%s.%s/" % (a.sub, a.domain)
    print("\nlive at (once the subdomain exists in hPanel):", url)
    print("or as a path:  https://%s/%s/" % (a.domain, a.sub))
    print("\nIf the subdomain does not resolve yet: hPanel → Domains → "
          "Subdomains → create '%s' → document root public_html/%s" % (a.sub, a.sub))


if __name__ == "__main__":
    main()
