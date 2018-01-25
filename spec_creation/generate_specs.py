"""
Used to generate specs.py from pdftotext created file
"""
import os


prelim_text = '''"""
Specs for the various files in the CSS 3.0 schema

Each tuple of tuples defines the name, storage type, external format, and
position of each field.


The schema was taken from here:

http://jkmacc-lanl.github.io/pisces/data/Anderson1990.pdf


"""
'''
var = '{table} = (\n'
form = '    ("{name}", {num}, "{type}", "{format}", {start}, {stop}),\n'
end = ')\n\n'

if __name__ == "__main__":
    out_file = 'specs.py'
    in_file = 'css3_tables.txt'
    outfi = open(out_file, 'w')
    fi = open(in_file, 'r')

    outfi.write(prelim_text)

    for line in fi.readlines():
        if line.startswith('Relation:'):
            table_name = line.split()[1]
            outfi.write(var.format(table=table_name))
        elif line.strip():
            split = line.split()
            fo = split[4].split('-')
            out = dict(name=split[0], num=int(split[1]), type=split[2],
                       format=split[3], start=int(fo[0]), stop=int(fo[1]))
            outfi.write(form.format(**out))
        elif not line.strip():
            outfi.write(end)

