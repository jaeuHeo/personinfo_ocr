import os
import re
import sys
import struct
import argparse
from io import BytesIO
from typing import BinaryIO, Tuple

import pdfminer
import fitz
from pdfminer.layout import LTImage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter, XMLConverter, HTMLConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from pdfminer.image import ImageWriter

from library.common import chmod


def maketheparser():
    parser = argparse.ArgumentParser(description=__doc__, add_help=True)
    parser.add_argument("files", type=str, default=None, nargs="+", help="File to process.")
    parser.add_argument("-d", "--debug", default=False, action="store_true", help="Debug output.")
    parser.add_argument("-p", "--pagenos", type=str, help="Comma-separated list of page numbers to parse. Included for legacy applications, use --page-numbers for more idiomatic argument entry.")
    parser.add_argument("--page-numbers", type=int, default=None, nargs="+", help="Alternative to --pagenos with space-separated numbers; supercedes --pagenos where it is used.")
    parser.add_argument("-m", "--maxpages", type=int, default=0, help="Maximum pages to parse")
    parser.add_argument("-P", "--password", type=str, default="", help="Decryption password for PDF")
    parser.add_argument("-o", "--outfile", type=str, default="-", help="Output file (default \"-\" is stdout)")
    parser.add_argument("-t", "--output_type", type=str, default="html", help="Output type: text|html|xml|tag (default is text)")
    parser.add_argument("-c", "--codec", type=str, default="utf-8", help="Text encoding")
    parser.add_argument("-s", "--scale", type=float, default=1.0, help="Scale")
    parser.add_argument("-A", "--all-texts", default=None, action="store_true", help="LAParams all texts")
    parser.add_argument("-V", "--detect-vertical", default=None, action="store_true", help="LAParams detect vertical")
    parser.add_argument("-W", "--word-margin", type=float, default=None, help="LAParams word margin")
    parser.add_argument("-M", "--char-margin", type=float, default=None, help="LAParams char margin")
    parser.add_argument("-L", "--line-margin", type=float, default=None, help="LAParams line margin")
    parser.add_argument("-F", "--boxes-flow", type=float, default=None, help="LAParams boxes flow")
    parser.add_argument("-Y", "--layoutmode", default="normal", type=str, help="HTML Layout Mode")
    parser.add_argument("-n", "--no-laparams", default=False, action="store_true", help="Pass None as LAParams")
    parser.add_argument("-R", "--rotation", default=0, type=int, help="Rotation")
    parser.add_argument("-O", "--output-dir", default='img', help="Output directory for images")
    parser.add_argument("-C", "--disable-caching", default=False, action="store_true", help="Disable caching")
    parser.add_argument("-S", "--strip-control", default=False, action="store_true", help="Strip control in XML mode")
    parser.add_argument("--save_name", default=None)
    return parser


def align32(x: int) -> int:
    return ((x+3)//4)*4


class BMPWriter:
    def __init__(
        self,
        fp: BinaryIO,
        bits: int,
        width: int,
        height: int
    ) -> None:
        self.fp = fp
        self.bits = bits
        self.width = width
        self.height = height
        if bits == 1:
            ncols = 2
        elif bits == 8:
            ncols = 256
        elif bits == 24:
            ncols = 0
        else:
            raise ValueError(bits)
        self.linesize = align32((self.width*self.bits+7)//8)
        self.datasize = self.linesize * self.height
        headersize = 14+40+ncols*4
        info = struct.pack('<IiiHHIIIIII', 40, self.width, self.height,
                           1, self.bits, 0, self.datasize, 0, 0, ncols, 0)
        assert len(info) == 40, str(len(info))
        header = struct.pack('<ccIHHI', b'B', b'M',
                             headersize+self.datasize, 0, 0, headersize)
        assert len(header) == 14, str(len(header))
        self.fp.write(header)
        self.fp.write(info)
        if ncols == 2:
            # B&W color table
            for i in (0, 255):
                self.fp.write(struct.pack('BBBx', i, i, i))
        elif ncols == 256:
            # grayscale color table
            for i in range(256):
                self.fp.write(struct.pack('BBBx', i, i, i))
        self.pos0 = self.fp.tell()
        self.pos1 = self.pos0 + self.datasize
        return

    def write_line(self, y: int, data: bytes) -> None:
        self.fp.seek(self.pos1 - (y+1)*self.linesize)
        self.fp.write(data)
        return


# class ImageWriter:
#     """Write image to a file
#
#     Supports various image types: JPEG, JBIG2 and bitmaps
#     """
#
#     def __init__(self, outdir: str, timename: str) -> None:
#         self.timename = timename
#         self.outdir = outdir
#         if not os.path.exists(self.outdir):
#             os.makedirs(self.outdir)
#         return
#
#     def export_image(self, image: LTImage) -> str:
#
#         (width, height) = image.srcsize
#
#         is_jbig2 = self.is_jbig2_image(image)
#         ext = self._get_image_extension(image, width, height, is_jbig2)
#         name, path = self._create_unique_image_name(self.outdir,
#                                                     self.timename, ext)
#
#         fp = open(path, 'wb')
#         if ext == '.jpg':
#             raw_data = image.stream.get_rawdata()
#             assert raw_data is not None
#             if LITERAL_DEVICE_CMYK in image.colorspace:
#                 from PIL import Image  # type ignore[import]
#                 from PIL import ImageChops
#                 ifp = BytesIO(raw_data)
#                 i = Image.open(ifp)
#                 i = ImageChops.invert(i)
#                 i = i.convert('RGB')
#                 i.save(fp, 'JPEG')
#             else:
#                 fp.write(raw_data)
#         elif is_jbig2:
#             input_stream = BytesIO()
#             input_stream.write(image.stream.get_data())
#             input_stream.seek(0)
#             reader = JBIG2StreamReader(input_stream)
#             segments = reader.get_segments()
#
#             writer = JBIG2StreamWriter(fp)
#             writer.write_file(segments)
#         elif image.bits == 1:
#             bmp = BMPWriter(fp, 1, width, height)
#             data = image.stream.get_data()
#             i = 0
#             width = (width+7)//8
#             for y in range(height):
#                 bmp.write_line(y, data[i:i+width])
#                 i += width
#         elif image.bits == 8 and LITERAL_DEVICE_RGB in image.colorspace:
#             bmp = BMPWriter(fp, 24, width, height)
#             data = image.stream.get_data()
#             i = 0
#             width = width*3
#             for y in range(height):
#                 bmp.write_line(y, data[i:i+width])
#                 i += width
#         elif image.bits == 8 and LITERAL_DEVICE_GRAY in image.colorspace:
#             bmp = BMPWriter(fp, 8, width, height)
#             data = image.stream.get_data()
#             i = 0
#             for y in range(height):
#                 bmp.write_line(y, data[i:i+width])
#                 i += width
#         else:
#             fp.write(image.stream.get_data())
#         fp.close()
#
#         return name
#
#     @staticmethod
#     def is_jbig2_image(image: LTImage) -> bool:
#         filters = image.stream.get_filters()
#         is_jbig2 = False
#         for filter_name, params in filters:
#             if filter_name in LITERALS_JBIG2_DECODE:
#                 is_jbig2 = True
#                 break
#         return is_jbig2
#
#     @staticmethod
#     def _get_image_extension(
#         image: LTImage,
#         width: int,
#         height: int,
#         is_jbig2: bool
#     ) -> str:
#         filters = image.stream.get_filters()
#         if len(filters) == 1 and filters[0][0] in LITERALS_DCT_DECODE:
#             ext = '.jpg'
#         elif is_jbig2:
#             ext = '.jb2'
#         elif (image.bits == 1 or
#               image.bits == 8 and
#               (LITERAL_DEVICE_RGB in image.colorspace or
#                LITERAL_DEVICE_GRAY in image.colorspace)):
#             ext = '.%dx%d.bmp' % (width, height)
#         else:
#             ext = '.%d.%dx%d.img' % (image.bits, width, height)
#         return ext
#
#     @staticmethod
#     def _create_unique_image_name(
#         dirname: str,
#         image_name: str,
#         ext: str
#     ) -> Tuple[str, str]:
#         name = image_name + ext
#         path = os.path.join(dirname, name)
#         img_index = 0
#         while os.path.exists(path):
#             name = '%s.%d%s' % (image_name, img_index, ext)
#             path = os.path.join(dirname, name)
#             img_index += 1
#         return name, path


def convert_pdf(path, format='text', codec='utf-8', password='',imagewriter=None):
    rsrcmgr = PDFResourceManager()
    retstr = BytesIO()
    laparams = LAParams()
    if format == 'text':
        device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams,imagewriter=imagewriter)
    elif format == 'html':
        device = HTMLConverter(rsrcmgr, retstr, codec=codec, laparams=laparams,imagewriter=imagewriter)
    elif format == 'xml':
        device = XMLConverter(rsrcmgr, retstr, codec=codec, laparams=laparams,imagewriter=imagewriter)
    else:
        raise ValueError('provide format, either text, html or xml!')
    fp = open(path, 'rb')
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    maxpages = 0
    caching = True
    pagenos=set()

    for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password,caching=caching, check_extractable=True):
        interpreter.process_page(page)

    text = retstr.getvalue().decode()

    fp.close()
    device.close()
    retstr.close()
    return text


def extract_text(files=[], outfile='-',
            _py2_no_more_posargs=None,  # Bloody Python2 needs a shim
            no_laparams=False, all_texts=None, detect_vertical=None, # LAParams
            word_margin=None, char_margin=None, line_margin=None, boxes_flow=None, # LAParams
            output_type='html', codec='utf-8', strip_control=False,
            maxpages=0, page_numbers=None, password="", scale=1.0, rotation=0,
            layoutmode='normal', output_dir='img', debug=False,
            disable_caching=False, save_name = '', **other):
    if _py2_no_more_posargs is not None:
        raise ValueError("Too many positional arguments passed.")
    if not files:
        raise ValueError("Must provide files to work upon!")

    if not no_laparams:
        laparams = pdfminer.layout.LAParams()
        for param in ("all_texts", "detect_vertical", "word_margin", "char_margin", "line_margin", "boxes_flow"):
            paramv = locals().get(param, None)

            if paramv is not None:
                setattr(laparams, param, paramv)
    else:
        laparams = None

    imagewriter = None
    # if output_dir:
    #     imagewriter = ImageWriter(output_dir)

    if output_type == "text" and outfile != "-":
        for override, alttype in (  (".htm", "html"),
                                    (".html", "html"),
                                    (".xml", "xml"),
                                    (".tag", "tag") ):
            if outfile.endswith(override):
                output_type = alttype

    if outfile == "-":
        outfp = sys.stdout

        if outfp.encoding is not None:
            codec = 'utf-8'
    else:
        outfp = open(outfile, "wb")

    html,text = '', ''
    for fname in files:
        with open(fname, "rb") as fp:

            # pdfresult = pdfminer.high_level.extract_text_to_fp(fp, **locals())
            html = html + convert_pdf(fname, format='html', codec='utf-8', password='',imagewriter=imagewriter)
            text = text + convert_pdf(fname, format='text', codec='utf-8', password='')
    return html,text


def pdf_extract(pdf_full_path, save_folder):
    split_name = pdf_full_path.split('/')[-1]
    time_name = split_name.split('.')[0]

    P = maketheparser()
    A = P.parse_args(args=[pdf_full_path, '--output-dir', save_folder,'--save_name',time_name])

    if A.page_numbers:
        A.page_numbers = set([x - 1 for x in A.page_numbers])
    if A.pagenos:
        A.page_numbers = set([int(x) - 1 for x in A.pagenos.split(",")])

    html,text = extract_text(**vars(A))

    fitz_pdf2img(pdf_full_path, save_folder)

    join_txt = re.sub('[^A-Za-z0-9가-힣]', '', text)

    return html, join_txt


def fitz_pdf2img(pdf_path, pdf_extract_path):
    doc = fitz.open(pdf_path)
    for i in range(len(doc)):
        for img in doc.get_page_images(i):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            if pix.n < 5:       # this is GRAY or RGB
                file_name = "p%s-%s.png" % (i, xref)
                file_full_path = os.path.join(pdf_extract_path, file_name)
                pix.save(file_full_path)
                chmod(file_full_path)
            else:               # CMYK: convert to RGB first
                file_name = "p%s-%s.png" % (i, xref)
                file_full_path = os.path.join(pdf_extract_path, file_name)
                pix1 = fitz.Pixmap(fitz.csRGB, pix)
                pix1.save(file_full_path)
                chmod(file_full_path)
