import glob
import gscholartex


suffix = "Google Scholar Citations.html"
for file in glob.glob("*" + suffix):
    surname = file.split(suffix)[0].split(" ")[-3]
    gscholartex.scholar_to_tex(file, surname + "Pubs.tex")
