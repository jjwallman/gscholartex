import itertools
from bs4 import BeautifulSoup
import datetime

# I have yet to work out how to automatically obtain a web page with more than
# 20 articles due to restrictions on the Google Scholar API

# The current workaround is to manually load the web page, click "show more",
# and save the resulting html


def clean_number(string):
    if string is None:
        return 0

    return ''.join(s for s in string if s.isdigit())


def reformat_entry(html_string, unwanted_strings):
    for phrase in unwanted_strings:
        if html_string.text.find(phrase) != -1:
            return None

    ref_data = html_string.contents[0].contents
    ret = {'title': ref_data[0],
           'authors': ref_data[1].contents[0]}

    journal = ref_data[2].contents[0]
    journal = journal.replace("arXiv preprint ", "")
    journal = journal.split("(")
    try:
        journal[1] = journal[1].split(")")[1]
    except IndexError:
        pass

    journal = "".join(journal)
    journal = journal.split(", ")
    try:
        journal[1] = "".join(itertools.takewhile(str.isdigit, journal[1]))
    except IndexError:
        pass

    ret['journal'] = ", ".join(journal)

    ret['year'] = clean_number(ref_data[2].contents[1].contents[0])

    try:
        ret['citations'] = int(html_string.contents[1].contents[0])
    except IndexError:
        ret['citations'] = 0

    return ret


def extract_publications(html_doc, unwanted_strings=None):
    """
    Extract publications and citation data from a saved Google Scholar page.

    Parameters
    ----------
    html_doc, str
        file name of the saved web page
    unwanted_strings, an iterable of str
        strings to filter out "publications" that should not be counted
    """
    if unwanted_strings is None:
        unwanted_strings = ["APS", "Bulletin"]

    f = open(html_doc, "r", encoding='utf8')
    doc = f.read()
    f.close()
    soup = BeautifulSoup(doc, 'html.parser')

    for a in soup.findAll('a'):
        a.replaceWithChildren()

    # Stripping out refs, buttons, etc
    labels = {'button': None,
              'td': {"class": "gsc_a_x"},
              'th': {'class': "gsc_a_x"},
              'tr': {'id': "gsc_a_tr0"}}

    for k, v in labels.items():
        if v is None:
            for entry in soup.findAll(k):
                entry.decompose()
        else:
            for entry in soup.findAll(k, v):
                entry.decompose()

    for div in soup.find_all('th', {'class': "gsc_a_t"}):
        for div2 in div.find_all('div', recursive=False):
            div2.decompose()

    pubs = soup.find_all('tr', {'class': 'gsc_a_tr'})
    pubs = [reformat_entry(pub, unwanted_strings) for pub in pubs]
    pubs = [pub for pub in pubs if pub is not None]

    cites = [int(c.contents[0]) for c in soup.find_all('span', {'class': 'gsc_g_al'})]
    years = [int(y.contents[0]) for y in soup.find_all('span', {'class': 'gsc_g_t'})]

    return pubs, {year: cite for year, cite in zip(years, cites)}


def citation_metrics(publications):
    """
    Return the h_index and total number of citations calculated from a list of
    publications.
    """
    cite_counts = sorted([v['citations'] for v in publications], reverse=True)
    for j, k in enumerate(cite_counts):
        if j + 1 > k:
            return j, sum(cite_counts)

    return len(cite_counts), sum(cite_counts)


def clean_cite(num_cites):
    if num_cites == 0:
        return ""
    if num_cites == 1:
        return " 1 citation."
    return " {} citations.".format(num_cites)


def bib_entry(publication):
    return "\\item {}. {}, {} ({}).{}\n".format(publication['title'],
                                                publication['authors'],
                                                publication['journal'],
                                                publication['year'],
                                                clean_cite(publication['citations']))


def scholar_to_tex(html_doc, output, unwanted_strings=None):
    """
    Extract publications and citation data from a saved Google Scholar page.
    The data is written to a file for inclusion in a LaTeX document.

    Parameters
    ----------
    html_doc, str
        file name of the saved web page
    output, str
        file name for the output
    unwanted_strings, an iterable of str
        strings to filter out "publications" that should not be counted
    """
    pubs, cites = extract_publications(html_doc, unwanted_strings)

    h_index, total_cites = citation_metrics(pubs)
    f = open(output, 'w')
    f.write("\\UseRawInputEncoding")
    f.write("\\newcommand{\\citedata}{%s}\n" % " ".join(str(a) for a in cites.items()))
    f.write("\\newcommand{\\citedate}{%s}\n" % datetime.date.today())
    f.write("\\newcommand{\\hindex}{%d}\n" % h_index)
    f.write("\\newcommand{\\numcites}{%d}\n" % total_cites)
    f.write("\\newcommand{\\printpubs}{%s}" %
            "".join([bib_entry(pub) for pub in pubs]))
    f.close()
