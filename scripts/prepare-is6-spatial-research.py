"""Archive primary references before the spatial-metric model contract."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
SOURCES={
    'einsteinpy-embedding-source.html':'https://docs.einsteinpy.org/en/stable/_modules/einsteinpy/hypersurface/schwarzschildembedding.html',
    'oist-gr-lecture8.pdf':'https://www.oist.jp/sites/default/files/2024-10/Lecture8.pdf',
    'gourgoulhon-schwarzschild-lecture2.pdf':'https://relativite.obspm.fr/blackholes/pdf/chennai/lecture2.pdf',
}


def main():
    folder=ROOT/'output/is6-spatial-research-20261101'
    if folder.exists():raise FileExistsError('Preserve research acquisition')
    folder.mkdir();rows=[]
    for name,url in SOURCES.items():
        row=dict(file=name,url=url,retrieved_utc=dt.datetime.now(dt.timezone.utc).isoformat())
        try:
            with urllib.request.urlopen(url,timeout=30) as response:
                data=response.read();row.update(final_url=response.url,content_type=response.headers.get_content_type())
            if name.endswith('.pdf') and not data.startswith(b'%PDF'):raise ValueError('Not a PDF')
            (folder/name).write_bytes(data)
            row.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),downloaded=True)
        except Exception as error:row.update(downloaded=False,error=str(error))
        rows.append(row)
        (folder/'acquisition.json').write_text(json.dumps(dict(accepted=False,sources=rows,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(row,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
