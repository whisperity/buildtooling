import codecs


def concatenate_files(header, source):
  """
  Read the specified header and source file and concatenate them in
  "header, source" order.
  """
  content = ""

  if (header):
    content = """
// +*************************************************************************+
//   Begin header file '%s'
// +*************************************************************************+

""" % header

    with codecs.open(header, 'r', encoding='utf-8', errors='replace') as hdr:
      content += hdr.read()

    content += """
// +*************************************************************************+
//   End header file '%s'
// +*************************************************************************+
""" % header

  if (source):
    content += """
// +*************************************************************************+
//   Begin implementation file '%s'
// +*************************************************************************+

""" % source

    with codecs.open(source, 'r', encoding='utf-8', errors='replace') as src:
      content += src.read()

    content += """
// +*************************************************************************+
//   End implementation file '%s'
// +*************************************************************************+

""" % source

  return content