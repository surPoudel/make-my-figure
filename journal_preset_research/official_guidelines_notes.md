# Official figure-preparation guidelines: retrieval notes and verbatim quotations

Access date: 2026-09-16. Method: `curl -L -A "Mozilla/5.0 ... Chrome/128 ..."` with HTML-to-text conversion in Python; PDFs read with PyMuPDF (fitz). Where a live page was blocked, the newest Internet Archive (Wayback Machine) capture returning HTTP 200 was used and is identified below. Quotations are verbatim (short excerpts). Bracketed remarks are mine.

Companion file: `official_guidelines_audit.csv` (159 rows; one row per requirement).

---

## 1. Nature / Nature Methods (Springer Nature) — all live pages retrieved

### 1.1 https://www.nature.com/nature/for-authors/formatting-guide (HTTP 200, live)
- "For guidance, Nature's standard figure sizes are 90 mm (single column) and 180 mm (double column) and the full depth of the page is 170 mm."
- "Lettering in figures (labelling of axes and so on) should be in lower-case type, with the first letter capitalized and no full stop."
- "Scale bars should be used rather than magnification factors."
- "Layering type directly over shaded or textured areas and using reversed type (white lettering on a coloured background) should be avoided where possible."
- "Where possible, text, including keys to symbols, should be provided in the legend rather than on the figure itself."
- "Legends should be fewer than 300 words each."
- Links to the current figure guide: http://research-figure-guide.nature.com/figures/ (this is the current "Preparing figures" resource; the URL https://www.nature.com/nature-portfolio/for-authors/preparing-figures returned HTTP 404).

### 1.2 https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/ (HTTP 200, live; footer "© 2026 Springer Nature")
- "We require: Axis lines and tick marks to be included; All axes to be labelled with units in parentheses, e.g. Data (unit); An accessible colour palette to be used (for example Wong, B. Points of view: Colour blindness. Nature Methods 8, 441 (2011).); Legible text (a minimum of 5 pt in size); Standard fonts (e.g. Arial or Helvetica) to be used"
- "We avoid: Background gridlines; Superfluous icons and other decorative elements; Drop shadows; Patterns; Text placed on top of busy images and hard-to-read backgrounds; Overlapping text; Coloured text; keylines, keys, etc. should be used instead"
- "Wherever possible, the Nature.com site will adhere to level AA of the Web Content Accessibility Guidelines (WCAG 2.1)"
- "We recommend supplying your artwork in the RGB colour spectrum. ... for print artwork will be automatically converted to CMYK."
- "All photographic images must be supplied at a minimum of 300 dpi. The maximum dpi of online proofs is 450 dpi; supplying images at 450 dpi or above ensures they will have the highest resolution possible."
- "For figures to be accepted all text needs to be legible and editable. Use standard fonts (e.g., Arial or Helvetica) ... Do not outline text; Embed fonts (True Type 2 or 42); Avoid coloured text; Maximum text size: 7 pt; Minimum text size: 5 pt"
- "All text should be a sans-serif typeface, preferably Helvetica or Arial. ... Separate panels in multi-panelled figures should be labelled with 8-pt bold, upright (not italic) and lowercase a, b, c, etc. Maximum text size for all other text is 7-pt and the minimum is 5-pt. Use Symbol font for glyphs and the Greek alphabet."
- "If you are using Python please use the following setting: Matplotlib.rcParams['pdf.fonttype']=42"
- "Exporting: .pdf or .eps preferred; All text, scale bars, boxes, etc. as vector artwork; RGB colour space; ... For images, minimum 450 dpi"

### 1.3 https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/ (HTTP 200, live)
- "The widths of printed figures are: 89 mm (single column); 183 mm (double column). The maximum height for a Nature figure is 170 mm, to allow space for the figure legend to fit underneath."
- "Authors are encouraged to submit figures at the smallest appropriate size, ensuring all fonts are between 5pt and 7pt. Nature reserves the right to make the final decision on figure size."
- "Avoiding red/green combinations and rainbow scales helps readers with colour blindness ... Keys or keylines should be used in the figure wherever possible, rather than having colour descriptions in the figure caption"
- Example colour-blind-safe palette (Wong): Black #000000; Orange #e69f00; Sky blue #56b4e9; Bluish green #009e73; Yellow #f0e442; Blue #0072b2; Vermillion #d55e00; Redish purple #cc79a7.
- "High contrast text (>4.5 contrast ratio) should be used"
- "For main figures we require vector files with editable layers. Nature's preferred formats are: .ai; .eps; .pdf (please choose to retain all editing capabilities)". Acceptable: layered Photoshop, PowerPoint (saved to PDF), .svg (plain), Excel, .ps. "We do not accept the following formats: .jpeg, .tiff, .png, Canvas, DeltaGraph, Tex, ChemDraw, SigmaPlot, Coreldraw." "Please limit file sizes to 50 MB where possible"
- Extended Data: "Files should be saved in RGB (not CMYK) ... Images should be supplied at a maximum resolution of 300 dpi. File size should not exceed 10 MB. Export and save each individual figure as a .jpeg (preferred), .tiff or .eps" ; "Tables can be set at one-column (8.9 cm) or two-column (18 cm) width."

### 1.4 https://research-figure-guide.nature.com/figures/extended-data-formatting-guidelines/ (HTTP 200, live)
- "Maximum page dimensions are 180 mm wide by 170 mm tall (170 mm to fit a legend underneath)."
- "Lines and strokes should be set between 0.25 and 1 pt."
- "Text should be maximum of 7 pt, minimum of 5 pt sans serif. Our line range is between 0.25 pt and 1 pt."
- Tables: "one-column (89 mm) or two column (180 mm) width" ; "please use 7-pt text".

### 1.5 https://www.nature.com/nature/for-authors/final-submission (HTTP 200, live)
- "Lettering should be in a sans-serif typeface, preferably Helvetica or Arial, the same font throughout all figures in the paper."
- "Separate panels in multi-part figures should each be labelled with 8 pt bold, upright (not italic) a, b, c. Maximum text size for all other text should be 7 pt; minimum text size should be 5 pt."
- "Nature's standard figure sizes are 89 mm wide (single column) and 183 mm wide (double column). The full depth of a Nature page is 247 mm. Figures can also be a column-and-a-half where necessary (120–136 mm)."
- "Line weights and strokes should be set between 0.25 and 1 pt at the final size (lines thinner than 0.25 pt may vanish in print)."
- "Layered Photoshop (PSD) or TIFF format (high resolution, 300–600 dots per inch (dpi) for photographic images" ; "JPEG (high-resolution, 300–600 dpi)" ; "All photographic images must be supplied at a minimum of 300 dpi at the maximum size they can be used."
- "Colour artwork can be provided in RGB (recommended) or CMYK format."

### 1.6 https://www.nature.com/nature/for-authors/initial-submission (HTTP 200, live)
- "Provide images in RGB color and at 300 dpi or higher resolution."
- "Use the same typeface (Arial or Helvetica) for all figures. Use symbol font for Greek letters."
- "Use distinct colors with comparable visibility and avoid the use of red and green for contrast. Recoloring primary data, such as fluorescence images, to color-safe combinations such as green and magenta or other accessible color palettes is strongly encouraged. Use of the rainbow color scale should be avoided."
- "Figures are best prepared at a width of 90 mm (single column) and 180 mm (double column) with a maximum height of 170mm.. At this size, the font size should be 5-7pt."
- "We require vector files with editable layers. Acceptable formats are: .ai, .eps, .pdf, .ps, .svg ... layered .psd or .tif ... .psd, .tif, .png or .jpg for bitmap images; .ppt if fully editable ... ChemDraw (.cdx)"

### 1.7 https://www.nature.com/nmeth/submission-guidelines/aip-and-formatting (HTTP 200, live) — Nature Methods
- "Figure panels should be prepared at a minimum resolution of 300 dpi and saved at a maximum width of 180 mm."
- "Use a 5–7 pt san serif font for standard text labelling and Symbol font for Greek characters."
- "Use scale bars, not magnification factors, and include error bars where appropriate."
- "Do not flatten labelling or scale/error bars onto images"
- "Include a brief title for each figure with a short description of each panel cited in sequence."
- Links to https://www.nature.com/documents/NRJs-guide-to-preparing-final-artwork.pdf as its "image preparation guidelines".
- Not specified on this page: panel-label style, line width, colour mode, accepted formats (these are given only in the linked NRJ PDF / research-figure-guide).

### 1.8 https://www.nature.com/documents/NRJs-guide-to-preparing-final-artwork.pdf (local copy /tmp/nrj_artwork.pdf; 2 pages; PDF metadata dated 2021-01-21) — "NATURE BRANDED RESEARCH JOURNALS GUIDE TO PREPARING FINAL ARTWORK"
- "All text should be sans-serif typeface, preferably Helvetica or Arial. Maximum text size is 7pt. Minimum text size is 5pt."
- "Original research content should be supplied in RGB colour mode. All other content (including Perspectives, Progress Articles and Review Articles) should be supplied in CMYK colour mode."
- Widths, original research and review content: "1-column width: 88 mm; 2-column width: 180 mm". All other content: "1-column width: 58 mm; 2-column width: 121 mm; 3-column width: 185 mm".
- Maximum height of figure by caption length: 1-column (88 mm) figures: <300 words ~130 mm, <150 words ~180 mm, <50 words ~220 mm; 2-column (180 mm) figures: <300 words ~185 mm, <150 words ~210 mm, <50 words ~225 mm.
- "Vector files: AI, EPS, PDF ... We cannot use bitmapped file types such as BMP, GIF, GIMP, JPG, PNG, Tex or TIFF for vector art."
- "All photos and complex technical illustrations ... should be directly saved/scanned in at least 300 dpi resolution at the maximum size that they could be used."
- "We recommend: AI, EPS, PDF, PPT ... We do not accept: BMP, GIF, GIMP, JPG, PNG, Tex, TIFF" ; "Try to keep each final figure to a maximum of 50 MB file size."
- "Do not add graphical effects (e.g. drop shadow, 3D rotate and bevel) to objects"

### 1.9 https://www.nature.com/documents/Extended_Data_guide.pdf (HTTP 200; 8 pages; PDF dated 2022-02-18)
- "Maximum page dimensions are 180 mm wide by 170 mm tall" ; "labelled with 8-pt bold, upright (not italic) and lowercase a, b, c, etc." ; "Maximum text size for all other text is 7-pt and the minimum is 5-pt." ; "Lines and strokes should be set between 0.25 and 1 pt." ; "Files must be saved in RGB" ; "JPEG, TIFF or EPS format" ; "must not exceed 10 Mb".

### Nature pages not retrieved
- https://www.nature.com/nature-portfolio/for-authors/preparing-figures — HTTP 404 (replaced by https://research-figure-guide.nature.com/figures/).
- https://www.nature.com/documents/Final_guide_to_authors.pdf (linked from final-submission page) — not attempted; superseded by the research-figure-guide site.

---

## 2. Science / Science Advances (AAAS) — live site blocked (Cloudflare HTTP 403 for curl, WebFetch and Playwright); Wayback captures used

### 2.1 Instructions for preparing an initial manuscript
Live URL https://www.science.org/content/page/instructions-preparing-initial-manuscript -> HTTP 403 ("Just a moment..."). Used: https://web.archive.org/web/20250810105213/https://www.science.org/content/page/instructions-preparing-initial-manuscript (latest 200-status capture; 2025-08-10).
- "It is best to create your figures as vector-based files, such as those produced by Adobe Illustrator. ... We cannot accept PowerPoint files or files that are not readable by Adobe Photoshop or Adobe Illustrator. When using Photoshop, please keep all labeling on a separate, editable layer if possible. To keep file sizes reasonable, please save images at a resolution of 300 dots per inch (dpi) for initial submission."
- "The width of figures, when printed, will usually be 5.7 cm (2.24 inches or 1 column), 12.1 cm (4.76 inches or 2 columns), or 18.4 cm (7.24 inches or 3 columns). Bar graphs, simple line graphs, and gels may be reduced to a smaller width. Symbols and lettering should be large enough to be legible after reduction [a reduced size of about 7 points (2.5 mm) high, and not smaller than 5 points]. Avoid wide variation in type size within a single figure."
- "The figure's title should be at the beginning of the figure caption, not in the figure itself. In general, explanatory text within the figure should be minimized relative to the text in the caption"
- "Keys to symbols, if needed, should be as simple as possible and positioned so that they do not needlessly enlarge the figure. Details can be put into the captions."
- "Size symbols so that they will be distinguishable when the figure is reduced (6 point minimum). Line widths should be legible upon reduction (minimum of 0.5 point at the final reduced size)."
- "Panels should be set close to each other, and common axis labels should not be repeated." ; "Do not use minor tick marks in scales or grid lines."
- "Avoid using red and green together, as this creates problems for individuals with color-deficient vision. Do not use colors that are similar in hue to identify different parts of a figure. Avoid using grayscale. Use white type and scale bars over darker areas of images."
- "Use a sans-serif font whenever possible (Helvetica is preferred)."
- "Capitalize only the first letter in a label, not every word"
- "Variables are always set in italics or as plain Greek letters (e.g., P, T, μ). The rest of the text in the figure should be plain or bold text. In a color figure, type atop a color region should be in bold face. Avoid using colored type."
- "Use capital letters for part labels in multipart figures – A, B, C, etc. These should be 10 pt and bold in the final figure. When possible, place part labels in the upper left corner of each figure part"
- Captions: "A short figure title should be included in bold-face type as the first line of the caption. ... No single caption should be longer than 200 words. ... Distinct figure panels should be labeled with uppercase letters (A, B, etc.)"
- Manuscript text (not figures): "For best results, use Times New Roman font. Avoid Symbol fonts if possible."
- Maximum figure height: not specified. Colour mode: not specified on Science pages.

### 2.2 Instructions for preparing a revised manuscript
Live URL https://www.science.org/content/page/instructions-preparing-revised-manuscript -> HTTP 403. Used: https://web.archive.org/web/20250330182956/https://www.science.org/content/page/instructions-preparing-revised-manuscript (2025-03-30).
- "The width of figures, when printed, will usually be 5.7 cm (2.24 inches or 1 column) or 12.1 cm (4.76 inches or 2 columns), or 18.4 cm (7.24 inches or 3 columns). ... [a reduced size of about 7 points (2.5 mm) high, and not smaller than 5 points]."
- "Line art that is not available as a vector file should have a resolution of at least 300 dots per inch (dpi), preferably higher, at final size ... Grayscale and color images should have a minimum resolution of 300 dpi at final size, and a higher resolution if possible."
- "Upsampling of images (i.e., artificially increasing file size or resolution) is not permitted."
- "Figure files at the revision stage must be in one of the following formats (in preferred order): Vector illustrations and diagrams (preferred): Adobe Portable Document Format (PDF) Encapsulated PostScript (EPS), or Adobe Illustrator (AI); Raster illustrations and diagrams: Tagged Image File Format (TIFF), minimum 300 dpi; Vector and raster combinations for photographs or microscopy images: PDF or EPS; Raster photographs or microscopy images: TIFF"
- "we cannot accept: Figures embedded in Microsoft Word files; Microsoft PowerPoint files"

### 2.3 Science Advances — Information for authors
Live URL https://www.science.org/content/page/science-advances-information-authors -> HTTP 403. Used: https://web.archive.org/web/20260709160938/https://www.science.org/content/page/science-advances-information-authors (2026-07-09).
- "You may include up to a total of ten figures and/or tables (combined) throughout the manuscript."
- "For initial submission, the figure files should appear in the combined PDF. They should be submitted as part of the online submission embedded in the Word file (with legend below)."
- "For best results, use universal fonts (such as Times New Roman) only, as special fonts may affect the rendering of your figure or table files."
- "Should your paper be accepted, you will have to ensure that your figures and tables follow our online publication specifications as described under Revised Manuscripts."
- Revised: "Figures should follow our Guide to Preparing Figures" -> https://www.science.org/cms/asset/7a6d912b-09dd-4fda-9ece-d07a47edb813/sciadv_guide_to_preparing_figures_2026.pdf
- Widths / dpi / min font / line width / panel-label size for Science Advances are NOT stated on this page; they are in the 2026 Guide to Preparing Figures PDF, which could not be retrieved (see below).
- CAUTION: A web-search snippet attributed to science.org states "Figures should default to widths of 1 column (3.55 in, 9 cm or 21p3 picas) or 2 columns (7.25 in, 18.4 cm or 43p6 picas)" and "All color figures must be supplied in RGB format (red, green, blue) and not CMYK". These sentences are NOT present in the retrieved 2026-07-09 capture and are recorded in the CSV as UNVERIFIED.

### Science pages / files not retrieved
- https://www.science.org/content/page/science-information-authors — live 403; Wayback captures since 2024 are themselves 403 block pages (no 200 capture found).
- https://www.science.org/content/page/preparing-manuscripts-using-latex — live 403; skipped (not figure-relevant).
- https://www.science.org/cms/asset/7a6d912b-09dd-4fda-9ece-d07a47edb813/sciadv_guide_to_preparing_figures_2026.pdf (and duplicate asset 76887697-...) — 403 via curl and WebFetch; not in Wayback (404).
- https://www.science.org/do/10.5555/page.2385607/full/author_prep_guide_2025-1752841600717.pdf and .../page.2385610/full/author_figure_prep_guide_2022-1723557116113.pdf (Science "figure preparation guide") — 403 live; not in Wayback.
- https://www.science.org/do/10.5555/science-advances-information-authors/full/science_advances-bio-1679063011003.docx — 403.

---

## 3. Cell Press (Elsevier) — live site blocked (HTTP 403 for curl and WebFetch); Wayback captures used

### 3.1 Cell Press Figure guidelines
Live URL https://www.cell.com/figureguidelines -> HTTP 403. Used: https://web.archive.org/web/20250911134049/https://www.cell.com/information-for-authors/figure-guidelines (Wayback resolved the redirect target; capture 2025-09-11, the newest available).
- "For initial submission and peer review, we can accept figures in a wide variety of formats, sizes, and resolutions. ... We recommend keeping the individual files small (1–2 MB)"
- "You must include a scale bar on all microscopy images."
- "Plot the individual data points in addition to indicating the average ± error for graphs displaying quantitation of a dataset."
- "Use a vector graphics program (such as Adobe Illustrator or Inkscape) to assemble the figures and verify that at final print size, each displayed image is at least 300 pixels per inch."
- "Main figures must be uploaded individually, as high-resolution image files. They should not be embedded in the main manuscript. The main figure titles and legends should not be part of the image files, but should instead appear at the end of the main manuscript file."
- "Each figure must fit on a single page. We recommend that figures be a maximum of 6.5 x 8 in (16.5 x 20 cm) to allow for page margins and text. ... Maximum widths are as follows: For the journal STAR Protocols: 13.4 cm (1 column) and 17.2 cm (full width of the page). For all other Cell Press journals, including partner journals: Two-column formats (such as research articles and reviews): 8.5 cm (1 column), 11.4 cm (1.5 columns), and 17.4 cm (full width of the page); Three-column formats (such as previews and commentaries): 5.5 cm (1 column), 11.4 cm (2 columns), and 17.4 cm (full width of the page)"
- "Each individual figure file should be no more than 20 MB."
- "For all other article types and journals, TIFF and PDF are the preferred formats for final production files." ; "Editorial Manager also accepts EPS, JPEG, and CDX files." ; "For the journal STAR Protocols, figures must be provided in JPG format." ; "The AI (Adobe Illustrator) file type should only be used for Leading Edge figures in the journal Cell."
- "Guidelines for artwork preparation ... Always embed fonts, and use only Arial fonts; When using layers, reduce to one layer (flatten artwork) before saving your image (except for Leading Edge papers published in Cell); Different panels should be labeled with capital letters; Text should be about 6–8 pt at the desired print size; Figure resolutions should be as follows: for color or grayscale figures, at least 300 dpi; for black and white figures, at least 500 dpi; for line-art figures, at least 1,000 dpi at the desired print size; ... If used, color should be encoded as RGB; To accommodate all viewers, red and green should not be used together (Color Vision by Cal Henderson is a helpful tool ...); Limit vertical space between parts of an illustration to only what is necessary for visual clarity; Line weights or stroke widths should be in the 0.5–1.5 pt range; Gray fills should be kept at least 20% different from other fills and no lighter than 10% or darker than 80%"
- ChemDraw: "Captions and atom labels* = Arial, 7 pt"
- Keys/legends inside figures: not specified beyond "legends should not be part of the image files".

### 3.2 Cell — Information for authors
Live URL https://www.cell.com/cell/authors -> HTTP 403 (and the 2026 Wayback captures are block pages). Used: https://web.archive.org/web/20250118195634/https://www.cell.com/cell/authors (latest 200 capture; 2025-01-18).
- "Each figure legend should have a brief title that describes the entire figure without citing specific panels, followed by a description of each panel. ... For any figures presenting pooled data, the measures should be defined in the figure legends (for example, "Data are represented as mean ± SEM.")."
- "Digital figure files submitted through Editorial Manager must conform to our digital figure guidelines or you will be asked to revise them. Please be aware that we may resize figures during the production process. The cost for color figures is $1,000 for the first color figure and $275 for each additional figure."
- Graphical abstract: "The image should be 1200 pixels square at 300 dpi, using Arial font with a size of 12–16 points; smaller fonts will not be legible online."
- STAR Methods: "If accepted, articles must adhere to the STAR Methods format." No figure sizing rules in the STAR Methods text; "Chemical structures should be included as high-resolution files according to Cell Press figure guidelines."

### 3.3 Cell Press graphical abstract guide (PDF)
Used: https://web.archive.org/web/20250911134249/https://cell.com/pb/assets/raw/shared/figureguidelines/GA_guide-1537202744020.pdf
- "Size: The submitted image should be 1200 pixels square at 300 dpi." ; "Font: Arial, 8–12 points. Smaller fonts will not be legible online." ; "Preferred file types: TIFF, PDF, JPG" [note: the Cell authors page says 12–16 points for the GA; the PDF says 8–12 points — discrepancy recorded as-is]
- "when in doubt, try to avoid red/green and red/black as comparative color choices."

### Cell pages not retrieved
- https://www.cell.com/figureguidelines and https://www.cell.com/cell/authors live — HTTP 403 (Cloudflare "Just a moment..."); newest usable Wayback captures were 2025-09-11 and 2025-01-18 respectively. Values may have changed since; re-check from a browser if needed.
- https://www.cell.com/star-methods and https://www.cell.com/star-authors-guide — no 200-status Wayback capture found since 2024; not retrieved.

---

## 4. Tooling notes
- Cloudflare blocked science.org and cell.com for curl (all header variants, HTTP/2, cookie jar), WebFetch, and headless Chromium (Playwright present but browser fails to launch: missing libnspr4).
- Wayback `id_` raw captures are sometimes gzip-compressed; decompressed in Python before text extraction.
- archive.org APIs intermittently returned 429 / "Temporarily Offline"; retries with delays succeeded.
