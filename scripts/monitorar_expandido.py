#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import urllib.parse  # garante urllib.parse carregado no módulo base
import monitorar as m

m.CONSULTAS = [
    '"Walter Ihoshi"',
    '"Walter Iihoshi"',
    '"Walter Shindi"',
    'Ihoshi',
    'Iihoshi',
    '"Walter Ihoshi" PSD',
    '"Walter Ihoshi" deputado',
    '"Walter Ihoshi" 5599',
    '"Walter Ihoshi" campanha',
    '"Walter Ihoshi" Marília',
]

if __name__ == '__main__':
    raise SystemExit(m.main())
