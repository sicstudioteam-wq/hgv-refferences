# HGV Reference Site

This repository contains the customer-facing HGV website reference set derived from the uploaded cPanel backup's `public_html` structure.

## Intentionally excluded

The uploaded backup was inspected before import. These were excluded because they are hosting/runtime, sensitive, duplicate, backup, internal, or unnecessary for static deployment:

- cPanel / CageFS runtime data
- SSL certificates and private keys
- mail data and server logs
- .ftpquota
- .well-known certificate validation files
- .htaccess / PHP runtime configuration
- source ZIP backups
- admin.html / internal admin artifacts
- backup HTML files
- XLSX / CSV internal working files
- README/change-log text files

The exact customer-facing manifest contains HTML, CSS, JSON, robots/sitemap and product/media assets.
