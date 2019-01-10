#!/usr/bin/env python3

from tkinter import *
from tkinter import messagebox
from tkinter import ttk
from tkinter import filedialog
import tkinter.font as tkfont

from pickle import load as pickle_load
from pickle import dump as pickle_dump

from subprocess import call as subp_call
from subprocess import Popen as subp_popen

import re
import datetime
import sys, os
import ntpath

try:
    # python 2
    from urllib2 import Request, urlopen, quote
except ImportError:
    # python 3
    from urllib.request import Request, urlopen, quote

try:
    # python 2
    from htmlentitydefs import name2codepoint
except ImportError:
    # python 3
    from html.entities import name2codepoint

# request google scholar for bibtex
GOOGLE_SCHOLAR_URL = "https://scholar.google.com"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

# to support relative path across linux, mac and windows

application_path = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the pyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app 
    # path into variable _MEIPASS'.
    application_path = os.path.dirname(sys.executable)

# configure
lib_file = os.path.join(application_path, "papers.dat")
conference_file = os.path.join(application_path, "conference.dat")
DEFAULT_YEAR = 1900
MAX_RATING = 5
OTHERS_CONFERENCE = 'others'

# Build a list of tuples for each file type the file dialog should display
my_filetypes = [('all files', '.*'), ('pdf files', '.pdf'), ('text files', '.txt')]
filetypes = tuple([ftype[1] for ftype in my_filetypes[1:]])

class Category:
    def __init__(self, label):
        self.label = label
        self.papers = set()     # paper ids

    # category_str: gui_input, multiple category separated by ';'
    @classmethod
    def parse(cls, category_str):
        items = category_str.split(';')
        category = []
        for item in items:
            item = item.strip()
            if len(item) < 1 : continue
            category.append(item)
        return category
    
    @classmethod
    def guiString(cls, categories):
        return ';'.join([c.label for c in categories])
    
    def __repr__(self):
        return self.label

author_format_re = re.compile(r'^(.+?),(.+?);(.*)')
author_format1_re = re.compile(r'^(.+?),(.+?) and (.*)')
class Author(Category):
    def __init__(self, label):
        self.last_name, self.first_name = self.nameParse(label)
        self.label = self.getFullname(self.first_name, self.last_name)
        self.papers = set()

    def getFullname(self, first_name, last_name):
        if len(self.last_name) > 0 and len(self.first_name) > 0:
            return self.last_name + ', ' + self.first_name
        elif len(self.last_name) > 0 :
            return self.last_name
        else: return ""
    
    @classmethod
    def nameParse(cls, full_name):
        tmp_names = re.split(',| ', full_name.strip())
        names = []
        for n in tmp_names:
            if len(n.strip()) > 0:
                names.append(n.strip())
        first_name = ""
        last_name = ""
        if len(names) > 0:
            last_name = names[0]
        if len(names) > 1 :
            first_name = names[-1]
        return last_name, first_name

    @classmethod
    def parseFormat1(cls, author_str):
        items = author_str.split(' and ')
        authors = []
        for item in items:
            item = item.strip()
            if len(item) < 1 : continue
            authors.append(item)
        return authors
    
    @classmethod
    def parseAuthorString(cls, author_str):
        m = author_format_re.match(author_str)
        m1 = author_format1_re.match(author_str)
        if m:
            items = cls.parse(author_str)
        elif m1:
            items = cls.parseFormat1(author_str)
        else:
            items = [author_str]
        return items

    @classmethod
    def authorParse(cls, author_str):
        items = cls.parseAuthorString(author_str)
        authors = []
        for item in items:
            authors.append(Author(item))
        return authors

    @classmethod
    def bibString(cls, authors):
        return ' and '.join([a.label for a in authors])
    
    @classmethod
    def guiString(cls, authors):
        return ';'.join([a.label for a in authors])

class Project(Category):

    @classmethod
    def projectParse(cls, project_str):
        items = cls.parse(project_str)
        projects = []
        for item in items:
            projects.append(Project(item))
        return projects

class Tag(Category):

    @classmethod
    def tagParse(cls, tag_str):
        items = cls.parse(tag_str)
        tags = []
        for item in items:
            tags.append(Tag(item))
        return tags

class Conference:
    def __init__(self, label):
        self.label = label
        self.index = 0
        self.papers = set()
    
    @staticmethod
    def loadConference(file_name):
        c_map = {}
        if os.path.isfile(file_name):
            with open(file_name) as fin:
                for line in fin.readlines():
                    line = line.strip().lower()
                    items = re.split('\t|    ', line)
                    if len(items) != 2: continue
                    c_map[items[0]] = items[1]
        return c_map
    
    def __repr__(self):
        return self.label

class Dataset(Category):
    
    @classmethod
    def datasetParse(cls, dataset_str):
        items = cls.parse(dataset_str)
        datasets = []
        for item in items:
            datasets.append(Dataset(item))
        return datasets

first_word_re = re.compile(r'^[a-zA-Z]+')
class Bib:
    
    def __init__(self):
        self._title = ""
        self._author = []
        self._conference = Conference(OTHERS_CONFERENCE)
        self._year = DEFAULT_YEAR
        
        self._first_title_word = ""
        self._first_author_name = ""

        self.bibtex = ""
        self.type = 0       # 0: conference, 1: jornal

    @property
    def title(self):
        return self._title
    
    @title.setter
    def title(self, value):
        self._title = value.lower()
        m = first_word_re.search(value)
        if m : self._first_title_word = m.group()
    
    @property
    def author(self):
        return self._author
    
    @author.setter
    def author(self, value):
        self._author = []
        self._first_author_name = ""
        if isinstance(value, str) and len(value) > 0:
            value = Author.authorParse(value.lower())
        if isinstance(value, list) and len(value) >= 1 :
            format_correct = True
            for v in value:
                if not isinstance(v, Author) : 
                    format_correct = False
                    break
            if format_correct:
                self._author = value
                self._first_author_name = value[0].last_name
    
    @property
    def conference(self):
        return self._conference
    
    @conference.setter
    def conference(self, value):
        self._conference = Conference(OTHERS_CONFERENCE)
        if isinstance(value, str) and len(value) > 0:
            value = Conference(value.lower())
        if isinstance(value, Conference) :
            self._conference = value
    
    @property
    def year(self):
        return self._year
    
    @year.setter
    def year(self, value):
        self._year = DEFAULT_YEAR
        if isinstance(value, str) and len(value) > 0:
            value = int(value)
        if isinstance(value, int) and value >= DEFAULT_YEAR and value <= datetime.datetime.now().year : 
            self._year = value
    
    def __repr__(self):
        tmp_cite = self._first_author_name + str(self.year)+ self._first_title_word
        if self.type == 1:
            return "@article{{{},\n  title={{{}}},\n  author={{{}}},\n  journal={{{}}},\n  year={{{}}}\n}}".format(tmp_cite, self.title, Author.bibString(self.author), self.conference.label, str(self.year))
        else:
            return "@inproceedings{{{},\n  title={{{}}},\n  author={{{}}},\n  booktitle={{{}}},\n  year={{{}}}\n}}".format(tmp_cite, self.title, Author.bibString(self.author), self.conference.label, str(self.year))

    def shortString(self):
        return " ".join([self.title, ' '.join([a.label for a in self.author]), str(self.year) if self.year!=DEFAULT_YEAR else ''])

type_re = re.compile(r'^@inproceedings(.*)')
title_re = re.compile(r'(?<=[^a-z]title\={).+?(?=})')
author_re = re.compile(r'(?<=[^a-z]author\={).+?(?=})')
conference_re = re.compile(r'(?<=[^a-z]booktitle\={).+?(?=})|(?<=[^a-z]journal\={).+?(?=})')
year_re = re.compile(r'(?<=[^a-z]year\={).+?(?=})')
gsbib_re = re.compile(r'<a href="https://scholar.googleusercontent.com(/scholar\.bib\?[^"]*)')
class bibParser:

    @classmethod
    def parse(cls, bib_str, lib=None):
        b = Bib()
        b.bibtex = bib_str
        b.type = cls.typeParser(bib_str)
        b.title = cls.titleParser(bib_str)
        b.author = cls.authorParser(bib_str, lib=lib)
        b.conference = cls.conferenceParser(bib_str, lib=lib)
        b.year = cls.yearParser(bib_str)
        return b
    
    @classmethod
    def typeParser(cls, bib_str):
        m = type_re.match(bib_str)
        return 0 if m else 1
    
    @classmethod
    def titleParser(cls, bib_str):
        m = title_re.search(bib_str)
        return m.group() if m else ""
    
    @classmethod
    def authorParser(cls, bib_str, lib=None):
        m = author_re.search(bib_str)
        a_str = m.group() if m else ""
        if lib is not None:
            authors = lib.parseAuthors(a_str)
            return authors
        return a_str
    
    @classmethod
    def conferenceParser(cls, bib_str, lib=None):
        m = conference_re.search(bib_str)
        c_str = m.group() if m else ""
        if lib is not None:
            conference = lib.parseConference(c_str)
            return conference
        return c_str
    
    @classmethod
    def yearParser(cls, bib_str):
        m = year_re.search(bib_str)
        return m.group() if m else ""
    
    # google scholar query
    # todo: download pdf
    @classmethod
    def query(cls, searchstr):
        """Query google scholar.

        This method queries google scholar and returns a list of citations.

        Parameters
        ----------
        searchstr : str
            the query

        Returns
        -------
        result : list of strings
            the list with citations

        """
        searchstr = '/scholar?q='+quote(searchstr)
        url = GOOGLE_SCHOLAR_URL + searchstr
        header = HEADERS
        header['Cookie'] = "GSP=CF=4"
        request = Request(url, headers=header)
        response = urlopen(request)
        html = response.read()
        html = html.decode('utf8')
        # grab the links
        tmp = cls.get_links(html)

        # follow the bibtex links to get the bibtex entries
        result = list()

        for link in tmp:
            url = GOOGLE_SCHOLAR_URL+link
            request = Request(url, headers=header)
            response = urlopen(request)
            bib = response.read()
            bib = bib.decode('utf8')
            result.append(bib)
        return result

    @classmethod
    def get_links(cls, html):
        """Return a list of reference links from the html.

        Parameters
        ----------
        html : str
        outformat : int
            the output format of the citations

        Returns
        -------
        List[str]
            the links to the references

        """
        reflist = gsbib_re.findall(html)
        # escape html entities
        reflist = [re.sub('&(%s);' % '|'.join(name2codepoint), lambda m:
                        chr(name2codepoint[m.group(1)]), s) for s in reflist]
        return reflist
    
class Paper(object):

    def __init__(self):
        # required information
        self.id = -1
        self.bib = Bib()
        self._path = ""     # relative path to support cloud storage
        
        # optional information
        self._dataset = []
        self._tag = []
        self._project = []

        self.comment = ""
        self.hasGithub = False
        self.hasRead = False
        self._rating = 0

        self._need_revise = False

    @property
    def bibtex(self):
        return self.bib.bibtex
    
    @bibtex.setter
    def bibtex(self, value):
        self.bib.bibtex = value
    
    @property
    def papertype(self):
        return self.bib.type
    
    @papertype.setter
    def papertype(self, value):
        self.bib.type = value

    @property
    def title(self):
        return self.bib.title
    
    @title.setter
    def title(self, value):
        self.bib.title = value
    
    @property
    def author(self):
        return Author.guiString(self.bib.author)
    
    @author.setter
    def author(self, value):
        self.bib.author = value

    @property
    def conference(self):
        return self.bib.conference.label
    
    @conference.setter
    def conference(self, value):
        self.bib.conference = value
    
    @property
    def year(self):
        return str(self.bib.year)

    @year.setter
    def year(self, value):
        self.bib.year = value

    @property
    def rating(self):
        return str(self._rating)

    @rating.setter
    def rating(self, value):
        self._rating = 0
        if isinstance(value, str) : value = int(value)
        if isinstance(value, int) and value >= 0 and value <= MAX_RATING:
            self._rating = value

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = ""
        normed_value = os.path.normpath(value)
        filename = ntpath.basename(normed_value)
        if filename.endswith(filetypes) and os.path.isfile(os.path.join(application_path, normed_value)):
            self._path = normed_value

    @property
    def full_path(self):
        return os.path.join(application_path, self._path)

    @property
    def dataset(self):
        return Dataset.guiString(self._dataset)
    
    @dataset.setter
    def dataset(self, value):
        self._dataset = []
        if isinstance(value, str) and len(value) > 0:
            value = Dataset.datasetParse(value)
        if isinstance(value, list) and len(value) >= 1 :
            format_correct = True
            for v in value:
                if not isinstance(v, Dataset) : 
                    format_correct = False
                    break
            if format_correct:
                self._dataset = value
    
    @property
    def tag(self):
        return Tag.guiString(self._tag)
    
    @tag.setter
    def tag(self, value):
        self._tag = []
        if isinstance(value, str) and len(value) > 0:
            value = Tag.tagParse(value)
        if isinstance(value, list) and len(value) >= 1 :
            format_correct = True
            for v in value:
                if not isinstance(v, Tag) : 
                    format_correct = False
                    break
            if format_correct:
                self._tag = value
    
    @property
    def project(self):
        return Project.guiString(self._project)
    
    @project.setter
    def project(self, value):
        self._project = []
        if isinstance(value, str) and len(value) > 0:
            value = Project.projectParse(value)
        if isinstance(value, list) and len(value) >= 1 :
            format_correct = True
            for v in value:
                if not isinstance(v, Project) : 
                    format_correct = False
                    break
            if format_correct:
                self._project = value

    def __repr__(self):
        return "title: {}\nauthor: {}\nconference: {}\nyear: {}\npath: {}\ntags: {}\ndataset: {}\nproject: {}\ncomment: {}\n{}\n".format(self.title, self.author, self.conference, self.year, self.full_path, self.tag, self.dataset, self.project, self.comment, 'Has released codes!' if self.hasGithub else 'No released codes!')
    
    def checkState(self):
        state = 0
        if self._path == "" :
            state = 1
        elif self.title == "" or self.author == "" or self.conference == "" or self.year == "" :
            state = 2
        return state

class Library:
    def __init__(self):
        self._years = {}     # {year:set(paper_id, ...), ...}

        self._authors = {}   # author_label: Author()
        self._conferences = {OTHERS_CONFERENCE:Conference(OTHERS_CONFERENCE)}   # conference_label: Conference()
        self._datasets = {}   # dataset_label: Conference()
        self._tags = {}   # tag_label: Conference()
        self._projects = {}   # project_label: Conference()
        self._ratings = {}      # rating: set(paper_id, ...)

        self._papers = {}   # paper_id: Paper()

        self._conference_alias = {OTHERS_CONFERENCE:OTHERS_CONFERENCE}
        self.paper_id_pool = set()
        self.max_paper_id = len(self._papers) - 1
    
    @property
    def papers(self):
        return self._papers
    
    @property
    def authors(self):
        return self._authors
    
    @property
    def conferences(self):
        return self._conferences
    
    @property
    def years(self):
        return self._years
    
    @property
    def datasets(self):
        return self._datasets

    @property
    def tags(self):
        return self._tags
    
    @property
    def projects(self):
        return self._projects
    
    @property
    def ratings(self):
        return self._ratings
    
    def parseConference(self, c_str):
        c_list = self.findConference(c_str.lower())
        re_c = c_list[0]
        # todo: compute similarity and pick up the similarer one
        for c in c_list:
            if c_str == c.label:
                re_c = c
        return re_c
    
    def parseAuthors(self, a_str):
        authors = []
        items = Author.parseAuthorString(a_str.lower())
        for item in items:
            last_name, first_name = Author.nameParse(item)
            full_name = last_name + ', ' + first_name
            a_list = self.findAuthor(full_name)
            if len(a_list) > 0:
                authors.append(a_list[0])
            else:
                authors.append(Author(full_name))
        return authors
    
    def parseTags(self, t_str):
        tags = []
        items = Tag.parse(t_str.lower())
        for item in items:
            t_list = self.findTag(item)
            if len(t_list) > 0:
                tags.append(t_list[0])
            else:
                tags.append(Tag(item))
        return tags
    
    def parseDatasets(self, d_str):
        datasets = []
        items = Dataset.parse(d_str.lower())
        for item in items:
            d_list = self.findDataset(item)
            if len(d_list) > 0:
                datasets.append(d_list[0])
            else:
                datasets.append(Dataset(item))
        return datasets
    
    def parseProjects(self, p_str):
        projects = []
        items = Project.parse(p_str.lower())
        for item in items:
            p_list = self.findProject(item)
            if len(p_list) > 0:
                projects.append(p_list[0])
            else:
                projects.append(Project(item))
        return projects
    
    def removePaper(self, paper_id):
        if paper_id in self.papers:
            del_paper = self.papers[paper_id]

            if del_paper.bib.year in self.years:
                self.years[del_paper.bib.year].remove(paper_id)
                if len(self.years[del_paper.bib.year]) == 0:
                    del self.years[del_paper.bib.year]

            del_paper.bib.conference.papers.remove(paper_id)

            for a in del_paper.bib.author:
                a.papers.remove(paper_id)
                if len(a.papers) == 0:
                    del self.authors[a.label]
            
            for t in del_paper._tag:
                t.papers.remove(paper_id)
                if len(t.papers) == 0:
                    del self.tags[t.label]
            
            for d in del_paper._dataset:
                d.papers.remove(paper_id)
                if len(d.papers) == 0:
                    del self.datasets[d.label]
            
            for p in del_paper._project:
                p.papers.remove(paper_id)
                if len(p.papers) == 0:
                    del self.projects[p.label]
            
            if del_paper._rating in self.ratings:
                self.ratings[del_paper._rating].remove(paper_id)
                if len(self.ratings[del_paper._rating]) == 0:
                    del self.ratings[del_paper._rating]

            del self._papers[paper_id]
            self.paper_id_pool.add(paper_id)
    
    # paper: Paper()
    def addPaper(self, paper):
        
        paper_id = self.generatePaperId()
        paper.id = paper_id

        self.addPaperYear(paper_id, paper.bib.year)
        self.addPaperRating(paper_id, paper._rating)

        paper.bib.conference.papers.add(paper_id)
        
        self.addPaperCategory(paper_id, paper.bib.author, self.authors)
        self.addPaperCategory(paper_id, paper._tag, self.tags)
        self.addPaperCategory(paper_id, paper._dataset, self.datasets)
        self.addPaperCategory(paper_id, paper._project, self.projects)

        self._papers[paper_id] = paper

        return paper_id
    
    def addPaperYear(self, paper_id, year):
        if year > DEFAULT_YEAR:
            tmp_paper_set = self._years.get(year, set())
            tmp_paper_set.add(paper_id)
            self._years[year] = tmp_paper_set
    
    def addPaperRating(self, paper_id, rating):
        if rating > 0 :
            tmp_paper_set = self._ratings.get(rating, set())
            tmp_paper_set.add(paper_id)
            self._ratings[rating] = tmp_paper_set
    
    def addPaperCategory(self, paper_id, categories, target_categories):
        for c in categories:
            if len(c.papers) == 0:
                target_categories[c.label] = c
            c.papers.add(paper_id)
    
    def revisePaperBib(self, paper_id, bib):
        hasRevised = False
        target_paper = self.papers[paper_id]

        if target_paper.bibtex != bib.bibtex:
            target_paper.bib.bibtex = bib.bibtex
            hasRevised = True

        if target_paper.papertype != bib.type:
            target_paper.bib.type = bib.type
            hasRevised = True

        if target_paper.title != bib.title:
            target_paper.bib.title = bib.title
            hasRevised = True
        
        if int(target_paper.year) != bib.year:
            if target_paper.bib.year in self.years:
                self.years[target_paper.bib.year].remove(paper_id)
                if len(self.years[target_paper.bib.year]) == 0 :
                    del self.years[target_paper.bib.year]
            self.addPaperYear(paper_id, bib.year)
            target_paper.bib.year = bib.year
            hasRevised = True

        if target_paper.conference != bib.conference.label:
            target_paper.bib.conference.papers.remove(paper_id)
            target_paper.bib.conference = bib.conference
            bib.conference.papers.add(paper_id)
            hasRevised = True

        if target_paper.author != Author.guiString(bib.author):
            target_paper.bib.author = self.revisePaperCategory(paper_id, bib.author, target_paper.bib.author, self.authors)
            hasRevised = True
        return hasRevised
    
    def revisePaper(self, paper_id, paper):
        hasRevised = False
        target_paper = self.papers[paper_id]

        if target_paper.path != paper.path :
            target_paper.path = paper.path
            hasRevised = True

        hasRevised = hasRevised | self.revisePaperBib(paper_id, paper.bib)

        if target_paper.tag != paper.tag:
            target_paper._tag = self.revisePaperCategory(paper_id, paper._tag, target_paper._tag, self.tags)
            hasRevised = True
        if target_paper.dataset != paper.dataset:
            target_paper._dataset = self.revisePaperCategory(paper_id, paper._dataset, target_paper._dataset, self.datasets)
            hasRevised = True
        if target_paper.project != paper.project:
            target_paper._project = self.revisePaperCategory(paper_id, paper._project, target_paper._project, self.projects)
            hasRevised = True

        if target_paper.comment != paper.comment:
            target_paper.comment = paper.comment
            hasRevised = True
        
        if target_paper.hasRead != paper.hasRead:
            target_paper.hasRead = paper.hasRead
            hasRevised = True
        if target_paper.hasGithub != paper.hasGithub:
            target_paper.hasGithub = paper.hasGithub
            hasRevised = True
        
        if target_paper.rating != paper.rating:
            if target_paper._rating in self.ratings:
                self.ratings[target_paper._rating].remove(paper_id)
                if len(self.ratings[target_paper._rating]) == 0:
                    del self.ratings[target_paper._rating]
            self.addPaperRating(paper_id, paper._rating)
            target_paper._rating = paper._rating
            hasRevised = True
        return hasRevised
    
    def revisePaperCategory(self, paper_id, source_category, target_category, categories):
        for c in source_category:
            c.papers.add(paper_id)
            if c.label not in categories:
                categories[c.label] = c
        for c in target_category:
            if c not in source_category:
                c.papers.remove(paper_id)
                if len(c.papers) == 0:
                    del categories[c.label]
        return source_category
        
    def setOtherConference(self, paper_id, paper):
        paper.bib._conference = self._conferences[OTHERS_CONFERENCE]
        self._conferences[OTHERS_CONFERENCE].papers.add(paper_id)

    def generatePaperId(self):
        if len(self.paper_id_pool) < 1:
            self.extendPaperIdPool()
        tmp_id = self.paper_id_pool.pop()
        return tmp_id
    
    def extendPaperIdPool(self):
        tmp_id = self.max_paper_id + 1
        while tmp_id in self.paper_id_pool:
            tmp_id += 1
        self.paper_id_pool.add(tmp_id)
        self.max_paper_id = tmp_id
    
    def similarity(self, str_a, str_b, support_fuzzy=False):
        if not support_fuzzy:
            return str_a.lower() == str_b.lower()
        if str_a in str_b or str_b in str_a :
            return True
        return False
    
    def searchDuplicatePaper(self, paper):
        for pi in self.papers:
            pi_path = self.papers[pi].path
            if paper.path == pi_path or paper.title == self.papers[pi].title or ntpath.basename(paper.path) == ntpath.basename(pi_path):
                return pi
        return -1

    # todo: better fuzzy comment
    def findPaper(self, paper, target_paper_ids=None, support_fuzzy=False, fuzzy_window=0):
        
        title_papers = set()
        author_papers = set()
        conference_papers = set()
        year_papers = set()
        tag_papers = set()
        dataset_papers = set()
        project_papers = set()

        if len(paper.title) > 0:
            title_papers = self.findTitle(paper.title, target_paper_ids=target_paper_ids, support_fuzzy=support_fuzzy)

        if paper.conference != OTHERS_CONFERENCE:
            conferences = self.findConference(paper.conference, support_fuzzy=support_fuzzy)
            conference_papers = self.combineListFindResults([c.papers for c in conferences])

        if paper.bib.year > DEFAULT_YEAR:
            year_papers = self.findYear(paper.year, fuzzy_window=fuzzy_window)
        
        if len(paper.author) > 0:
            authors = []
            for a in paper.bib.author:
                authors.extend(self.findAuthor(a.label, support_fuzzy=support_fuzzy))
            author_papers = self.combineListFindResults([a.papers for a in authors])
        
        if len(paper.tag) > 0:
            tags = []
            for t in paper._tag:
                tags.extend(self.findTag(t.label, support_fuzzy=support_fuzzy))
            tag_papers = self.combineListFindResults([t.papers for t in tags])
        
        if len(paper.dataset) > 0:
            datasets = []
            for d in paper._dataset:
                datasets.extend(self.findDataset(d.label, support_fuzzy=support_fuzzy))
            dataset_papers = self.combineListFindResults([d.papers for d in datasets])
        
        if len(paper.project) > 0:
            projects = []
            for p in paper._project:
                projects.extend(self.findProject(p.label, support_fuzzy=support_fuzzy))
            project_papers = self.combineListFindResults([p.papers for p in projects])
        
        tmp_papers, isAnd = self.combineTwoFindResults(title_papers, author_papers, len(paper.title) > 0, len(paper.author) > 0)

        tmp_papers, isAnd = self.combineTwoFindResults(tmp_papers, conference_papers, isAnd, paper.conference != OTHERS_CONFERENCE)

        tmp_papers, isAnd = self.combineTwoFindResults(tmp_papers, year_papers, isAnd, paper.bib.year > DEFAULT_YEAR)
        
        tmp_papers, isAnd = self.combineTwoFindResults(tmp_papers, tag_papers, isAnd, len(paper.tag) > 0)
        
        tmp_papers, isAnd = self.combineTwoFindResults(tmp_papers, dataset_papers, isAnd, len(paper.dataset) > 0)
        
        tmp_papers, isAnd = self.combineTwoFindResults(tmp_papers, project_papers, isAnd, len(paper.project) > 0)
        
        if target_paper_ids is not None:
            tmp_papers =[pi for pi in tmp_papers if pi in target_paper_ids]
        return tmp_papers
    
    def combineTwoFindResults(self, papers1, papers2, isAnd1, isAnd2):
        papers = set()
        isAnd = False
        if isAnd1 and isAnd2:
            papers = papers1 & papers2
            isAnd = True
        elif isAnd1:
            papers = papers1
            isAnd = True
        elif isAnd2:
            papers = papers2
            isAnd = True
        return papers, isAnd

    def combineListFindResults(self, papers_list, isAnd=True):
        re_papers = set()
        if len(papers_list) > 0 :
            if isAnd:
                re_papers = papers_list[0].intersection(*papers_list[1:])
            else:
                re_papers = papers_list[0].union(*papers_list[1:])
        return re_papers

    def findYear(self, year, fuzzy_window=0):
        papers = set()
        year = int(year)
        if year in self.years:
            papers |= self.years[year]
        if fuzzy_window > 0:
            for i in range(fuzzy_window):
                if year+1+i in self.years:
                    papers |= self.years[year+1+i]
                if year-i-1 in self.years:
                    papers |= self.years[year-i-1]
        return papers
    
    def findRating(self, rating):
        papers = set()
        rating = int(rating)
        if rating in self.ratings:
            papers |= self.ratings[rating]
        return papers
    
    def findUnread(self):
        papers = [pi for pi in self.papers if not self.papers[pi].hasRead]
        return set(papers)
    
    def findGithub(self):
        papers = [pi for pi in self.papers if self.papers[pi].hasGithub]
        return set(papers)
    
    def findToRevise(self):
        papers = [pi for pi in self.papers if self.papers[pi]._need_revise]
        return set(papers)

    def findTitle(self, t_str, target_paper_ids=None, support_fuzzy=False):
        papers = set()
        if target_paper_ids is None:
            target_paper_ids = self._papers
        for pi in target_paper_ids:
            if self.similarity(t_str, self._papers[pi].title, support_fuzzy=support_fuzzy):
                papers.add(pi)
        return papers

    def getConferenceName(self, c_str):
        return self._conference_alias[c_str] if c_str in self._conference_alias else OTHERS_CONFERENCE
    
    def findConference(self, c_str, support_fuzzy=False):
        conferences = []
        if c_str != OTHERS_CONFERENCE:
            for c_name in self._conference_alias:
                if c_str == c_name or c_name in c_str :
                    conferences.append(self.conferences[self._conference_alias[c_name]])
                elif support_fuzzy and self.similarity(c_str, c_name, support_fuzzy=support_fuzzy):
                    conferences.append(self.conferences[self._conference_alias[c_name]])
        return conferences if len(conferences) > 0 else [self._conferences[OTHERS_CONFERENCE]]
    
    def findItems(self, key_words, item_dict, support_fuzzy=False):
        items = []
        if key_words in item_dict:
            items.append(item_dict[key_words])
        if support_fuzzy:
            for item_str in item_dict:
                if key_words in item_dict: continue
                if self.similarity(key_words, item_str, support_fuzzy=support_fuzzy):
                    items.append(item_dict[item_str]) 
        return items
    
    def findAuthor(self, a_str, support_fuzzy=False):
        return self.findItems(a_str, self._authors, support_fuzzy=support_fuzzy)
    
    def findDataset(self, d_str, support_fuzzy=False):
        return self.findItems(d_str, self._datasets, support_fuzzy=support_fuzzy)
    
    def findTag(self, t_str, support_fuzzy=False):
        return self.findItems(t_str, self._tags, support_fuzzy=support_fuzzy)

    def findProject(self, p_str, support_fuzzy=False):
        return self.findItems(p_str, self._projects, support_fuzzy=support_fuzzy)

class MyDialog(Toplevel):
    def __init__(self, parent, prompt):
        Toplevel.__init__(self, parent)
        self.re = False

        self.label = Label(self, text="Found the following repeated papers, delete them all or cancel for delete them on your own!")
        self.text = Text(self)
        self.text.insert(1.0, prompt)

        self.del_button = ttk.Button(self, text="Delete All", command=self.deleteALL)
        self.cancel_button = ttk.Button(self, text="Cancel", command=self.destroy)

        self.label.pack(side="top", fill="x")
        self.text.pack(side="top", fill="x")
        self.del_button.pack(side="left", anchor="e", padx=4, pady=4)
        self.cancel_button.pack(side="left")

        self.transient(parent)
    
    def deleteALL(self):
        self.re = True
        self.destroy()

    def show(self):
        self.grab_set()
        self.wait_window()
        return self.re

class LibraryGUI:

    def __init__(self):
        self.lib = Library()
        self.cur_paper = Paper()
        self.paper_to_tree = {}
        self.authorize_conference_list = []
        self.removed_files = []

        self.display_columns = ('Title', 'Conference', 'Year', 'Read', 'Rating')
        self.display_columns_values = lambda x: (x.title, x.conference, x.year, '1' if x.hasRead else '0', x.rating)

        # gui style
        self.display_column_width = {'Title':300, 'Conference':110, 'Year':60, 'Read':50, 'Rating':70}
        self.fontSize = 16
        self.textfontSize = 14
        self.headFontSize = 14
        self.cellWidth = 6

        # gui
        self.root = Tk()
        self.root.title("Cloud Paper Manager")
        self.root.minsize(width=1280, height= 650)
        # self.root.resizable(width=False, height=False)

        self.filter_frame = ttk.Frame(self.root)
        self.display_frame = ttk.Frame(self.root)
        self.info_frame = ttk.Frame(self.root)

        # filter

        self.labelCategoryInput = ttk.Label(self.filter_frame, text='FilterBy')
        filter_type_var = StringVar()
        self.filter_category = ttk.Combobox(self.filter_frame, textvariable=filter_type_var, width=int(1*self.cellWidth))

        self.display_filter = Listbox(self.filter_frame, width=int(1*self.cellWidth))  # lists of existing filters
        self.df_yscroll = ttk.Scrollbar(self.filter_frame, command=self.display_filter.yview, orient=VERTICAL)
        self.display_filter.configure(yscrollcommand=self.df_yscroll.set)

        self.progress = ttk.Progressbar(self.filter_frame, orient=HORIZONTAL, mode='determinate')

        # display paper
        self.display_papers = ttk.Treeview(self.display_frame)  # lists of existing papers
        self.dp_yscroll = ttk.Scrollbar(self.display_frame, command=self.display_papers.yview, orient=VERTICAL)
        self.display_papers.configure(yscrollcommand=self.dp_yscroll.set)

        # bibtex parser
        self.labelBibInput = ttk.Label(self.info_frame, text='Bibtex:')
        self.add_bib_input = Text(self.info_frame, height=5, width=4*self.cellWidth)
        self.add_bib_input.bind("<Tab>", self.focus_next_widget)
        self.bib_parser_button = ttk.Button(self.info_frame, command = self.parseBib, text = "Parse", width=self.cellWidth)
        self.bib_clear_button = ttk.Button(self.info_frame, command = self.clearBibtex, text = "Clear", width=self.cellWidth)

        self.labelTitleInput = ttk.Label(self.info_frame, text='Title:')
        self.add_title_input = ttk.Entry(self.info_frame, width=4*self.cellWidth)

        self.labelAuthorInput = ttk.Label(self.info_frame, text='Authors:')
        self.add_author_input = ttk.Entry(self.info_frame, width=4*self.cellWidth)

        self.labelConferenceInput = ttk.Label(self.info_frame, text='Conf.:')
        c_var = StringVar()
        self.add_conference = ttk.Combobox(self.info_frame, textvariable=c_var, width=int(1.9*self.cellWidth))
        
        self.labelYearInput = ttk.Label(self.info_frame, text='Year:')
        self.spinval = StringVar()
        self.add_year_input = Spinbox(self.info_frame, from_=DEFAULT_YEAR, to=datetime.datetime.now().year, textvariable=self.spinval, width=self.cellWidth)

        self.labelPathInput = ttk.Label(self.info_frame, text='Path:')
        self.add_path_input = ttk.Entry(self.info_frame, width=3*self.cellWidth)

        self.path_button = ttk.Button(self.info_frame, command = self.browseFiles, text = "...", width=self.cellWidth)

        self.labelTagInput = ttk.Label(self.info_frame, text='Tags:')
        self.add_tag_input = ttk.Entry(self.info_frame, width=4*self.cellWidth)

        self.labelProjectInput = ttk.Label(self.info_frame, text='Projects:')
        self.add_project_input = ttk.Entry(self.info_frame, width=4*self.cellWidth)

        self.labelDatasetInput = ttk.Label(self.info_frame, text='Datasets:')
        self.add_dataset_input = ttk.Entry(self.info_frame, width=4*self.cellWidth)

        self.labelCommentInput = ttk.Label(self.info_frame, text='Notes:')
        self.add_comment_input = Text(self.info_frame, height=3, width=4*self.cellWidth)
        self.add_comment_input.bind("<Tab>", self.focus_next_widget)

        self.labelRatingInput = ttk.Label(self.info_frame, text='Rating:')
        self.r_spinval = StringVar()
        self.add_rating_input = Spinbox(self.info_frame, from_=0, to=MAX_RATING, textvariable=self.r_spinval,width=self.cellWidth)

        self.hasRead = BooleanVar()
        self.read_check = ttk.Checkbutton(self.info_frame, text='Read', variable=self.hasRead,
	    onvalue=True, offvalue=False, width=self.cellWidth)

        self.hasGithub = BooleanVar()
        self.github_check = ttk.Checkbutton(self.info_frame, text='Code', variable=self.hasGithub,
	    onvalue=True, offvalue=False, width=self.cellWidth)

        self.add_button = ttk.Button(self.info_frame, command = self.addPaper, text = "Add", width=self.cellWidth)
        self.del_button = ttk.Button(self.info_frame, command = self.delPaper, text = "Del", width=self.cellWidth)
        self.revise_button = ttk.Button(self.info_frame, command = self.revisePaper, text = "Edit", width=self.cellWidth)
        self.find_button = ttk.Button(self.info_frame, command = self.findPaper, text = "Find", width=self.cellWidth)
        self.reset_button = ttk.Button(self.info_frame, command = self.resetMode, text = "Reset", width=self.cellWidth)
        self.serialize_button = ttk.Button(self.info_frame, command = self.serialize, text = "Sync", width=self.cellWidth)

        self.reparse_button = ttk.Button(self.info_frame, command = self.reparse, text = "Renew", width=self.cellWidth)
        self.gScholar_button = ttk.Button(self.info_frame, command = self.fetchGS, text = "Web", width=self.cellWidth)
        self.import_button = ttk.Button(self.info_frame, command = self.importFiles, text = "Import", width=self.cellWidth)

    def focus_next_widget(self, event):
        event.widget.tk_focusNext().focus()
        return("break")

    def init(self):
        self.initLib()
        self.initConference(conference_file)
        self.initWindow()
        self.initButtons()
        self.initStyle()
    
    def initStyle(self):
        # font
        # The default for all GUI items not otherwise specified.
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(size=self.fontSize)

        # Used for entry widgets, listboxes, etc.
        text_font = tkfont.nametofont('TkTextFont')
        text_font.configure(size=self.fontSize)

        # A standard fixed-width font. for Text widget
        text_font = tkfont.nametofont('TkFixedFont')
        text_font.configure(size=self.textfontSize)

        # The font typically used for column headings in lists and tables.
        text_font = tkfont.nametofont('TkHeadingFont')
        text_font.configure(size=self.headFontSize)

        # TkMenuFont	The font used for menu items.
        # TkCaptionFont	A font for window and dialog caption bars.
        # TkSmallCaptionFont	A smaller caption font for subwindows or tool dialogs
        # TkIconFont	A font for icon captions.
        # TkTooltipFont	A font for tooltips.
        text_font = tkfont.nametofont('TkIconFont')     # file dialog filename font
        text_font.configure(size=self.headFontSize)

        text_font = tkfont.nametofont('TkCaptionFont')      # dialog text font
        text_font.configure(size=self.fontSize)
    
    def initLib(self):
        # load existing papers
        self.deserialize()
        self.displayPaper(self.lib.papers)

        self.other_filter_set = {'unRead': self.lib.findUnread, 'hasGithub': self.lib.findGithub, 'needRevise':self.lib.findToRevise}

        self.filter_dict = {'conference': self.lib.conferences, 'year':self.lib.years, 'author':self.lib.authors, 'dataset':self.lib.datasets, 'tag':self.lib.tags, 'project':self.lib.projects, 'rating':self.lib.ratings, 'others': self.other_filter_set}
        self.filter_type_list = list(self.filter_dict.keys())

    def initWindow(self):
        self.root.protocol("WM_DELETE_WINDOW", self.closeWindow)
        # filter
        self.filter_category['value'] = ['please select'] + self.filter_type_list
        self.filter_category['state'] = "readonly"
        self.filter_category.current(0)
        self.filter_category.bind('<<ComboboxSelected>>', self.filterListingEvent)

        self.display_filter.bind("<<ListboxSelect>>", self.filteredPaperEvent)

        # display paper
        self.display_papers['columns'] = self.display_columns
        # self.display_papers.heading('#0', text='Title')
        # hide #0 column
        self.display_papers['show'] = 'headings'
        # sort column
        for col in self.display_columns:
            self.display_papers.heading(col, text=col, command=lambda _col=col: \
                     self.treeview_sort_column(self.display_papers, _col, False))
            if col == 'Title':
                self.display_papers.column(col, minwidth=self.display_column_width[col], width=self.display_column_width[col], stretch=1, anchor='w')
            else:
                self.display_papers.column(col, minwidth=self.display_column_width[col], width=self.display_column_width[col], stretch=0, anchor='center')

        self.display_papers.bind("<ButtonRelease-1>", self.clickPaperEvent)
        self.display_papers.bind("<<TreeviewSelect>>", self.selectPaperEvent)
        self.display_papers.bind("<Double-1>", self.openPaperEvent)

        # generate conference combobox
        self.add_conference['value'] = ['please select'] + self.authorize_conference_list
        self.add_conference['state'] = "readonly"
        self.add_conference.current(0)

    def treeview_sort_column(self, tv, col, reverse):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        l.sort(reverse=reverse)

        # rearrange items in sorted positions
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)

        # reverse sort next time
        tv.heading(col, command=lambda: \
                self.treeview_sort_column(tv, col, not reverse))
    
    def initButtons(self):
        # button logic
        # self.bib_parser_button
        # self.add_button
        # self.reset_button
        self.del_button.config(state=DISABLED)     # .config(state=NORMAL)
        # self.find_button
        self.revise_button.config(state=DISABLED) 
        self.serialize_button.config(state=DISABLED)
    
    def initConference(self, c_map_file):
        c_map = Conference.loadConference(c_map_file)
        for c_str in c_map:
            new_authorized_cstr = c_map[c_str]
            c_name = self.lib.getConferenceName(new_authorized_cstr)
            if c_name == OTHERS_CONFERENCE:
                self.lib._conferences[new_authorized_cstr] = Conference(new_authorized_cstr)
                self.lib._conference_alias[c_str] = new_authorized_cstr
                self.lib._conference_alias[new_authorized_cstr] = new_authorized_cstr
            else:
                self.lib._conference_alias[c_str] = c_name
                self.lib._conference_alias[new_authorized_cstr] = c_name
        
        for c_str in self.lib.conferences:
            self.authorize_conference_list.append(c_str)
            self.lib.conferences[c_str].index = len(self.authorize_conference_list)

    # finish gui arrange
    def gui_arrang(self):
        padding = 10
        self.filter_frame.pack(side = LEFT, fill='both', expand=False, padx=(padding,0), pady=(padding,padding))
        # self.filter_frame.columnconfigure(0, weight=1)
        self.filter_frame.rowconfigure(2, weight=1)

        self.display_frame.pack(side = LEFT, fill='both', expand=True, padx=(0,0), pady=(padding,padding))
        self.display_frame.columnconfigure(1, weight=3)
        self.display_frame.rowconfigure(0, weight=1)

        self.info_frame.pack(side = LEFT, fill='both', expand=True, padx=(0,padding), pady=(padding,padding))
        self.info_frame.columnconfigure(0, weight=0)
        self.info_frame.columnconfigure(1, weight=1)
        self.info_frame.columnconfigure(2, weight=0)
        self.info_frame.columnconfigure(3, weight=1)
        self.info_frame.columnconfigure(4, weight=0)
        self.info_frame.rowconfigure(2, weight=1)
        self.info_frame.rowconfigure(15, weight=1)

        # filter
        self.labelCategoryInput.grid(row=0, column=0, sticky=E)
        self.filter_category.grid(row=1, column=0, columnspan=2, sticky=(W,E))
        self.progress.grid(row=0, column=1, sticky=(W,S,E))

        self.display_filter.grid(row=2, column=0, columnspan=2, sticky=(N,W,E,S))
        self.df_yscroll.grid(row=2, column=2, sticky=(N,W,S))

        # display papers 19 columns, 13 rows

        self.display_papers.pack(side = LEFT, fill='both', expand=True)
        self.dp_yscroll.pack(side = LEFT, fill='both', expand=False)

        # global buttons

        self.import_button.grid(row=0,column=0)
        self.gScholar_button.grid(row=0,column=1)
        self.reset_button.grid(row=0,column=2)
        self.serialize_button.grid(row=0,column=3)
        self.reparse_button.grid(row=0, column=4)

        # paper bib data

        self.labelBibInput.grid(row=1, column=0, sticky=(N,E))
        self.add_bib_input.grid(row=1, column=1, columnspan=4, rowspan=5, sticky=(N,E,W,S))
        self.bib_parser_button.grid(row=6, column=3)
        self.bib_clear_button.grid(row=6, column=4)

        self.labelTitleInput.grid(row=7,column=0, sticky=E)
        self.add_title_input.grid(row=7,column=1, columnspan=4, sticky=(N,E,W,S))

        self.labelAuthorInput.grid(row=8,column=0, sticky=E)
        self.add_author_input.grid(row=8,column=1, columnspan=4, sticky=(N,E,W,S))

        self.labelConferenceInput.grid(row=9,column=0, sticky=E)
        self.add_conference.grid(row=9,column=1, columnspan=2, sticky=W)

        self.labelYearInput.grid(row=9,column=3, sticky=E)
        self.add_year_input.grid(row=9,column=4, sticky=W)

        self.labelPathInput.grid(row=10,column=0, sticky=E)
        self.add_path_input.grid(row=10,column=1, columnspan=3, sticky=(N,E,W,S))
        self.path_button.grid(row=10, column=4, sticky=W)

        # paper optional data

        self.labelTagInput.grid(row=11,column=0, sticky=E)
        self.add_tag_input.grid(row=11,column=1, columnspan=4, sticky=(N,E,W,S))

        self.labelProjectInput.grid(row=12,column=0, sticky=E)
        self.add_project_input.grid(row=12,column=1, columnspan=4, sticky=(N,E,W,S))

        self.labelDatasetInput.grid(row=13,column=0, sticky=E)
        self.add_dataset_input.grid(row=13,column=1, columnspan=4, sticky=(N,E,W,S))

        self.labelCommentInput.grid(row=14,column=0, sticky=(N,E))
        self.add_comment_input.grid(row=14,column=1, columnspan=4, rowspan=3, sticky=(N,E,W,S))

        self.labelRatingInput.grid(row=17,column=0, sticky=E)
        self.add_rating_input.grid(row=17,column=1, sticky=W)

        self.read_check.grid(row=17,column=2)
        self.github_check.grid(row=17,column=3)

        self.add_button.grid(row=18,column=1)
        self.revise_button.grid(row=18,column=2)
        self.find_button.grid(row=18,column=3)
        self.del_button.grid(row=18,column=4)
    
    def serialize(self):
        f = open(lib_file, 'wb')
        pickle_dump(self.lib, f)
        if len(self.removed_files)>0 and messagebox.askokcancel("Delete Local File!","Do you want to delete local files of removed papers?\n" + '\n'.join([os.path.relpath(f, application_path) for f in self.removed_files]) ) :
            for f in self.removed_files:
                if os.path.isfile(f) :
                    os.remove(f)
            self.removed_files.clear()
        messagebox.showinfo(message='Save lib data success!')
        self.unserializeMode()
    
    def deserialize(self):
        if os.path.isfile(lib_file):
            f = open(lib_file, 'rb')
            self.lib = pickle_load(f)

    # main modes
    
    def selectMode(self):
        self.displayData(self.cur_paper)

        self.add_button.config(state=DISABLED)
        self.find_button.config(state=DISABLED)
        self.del_button.config(state=NORMAL)
        self.revise_button.config(state=NORMAL)
    
    def addMode(self):
        # reset cur paper
        self.cur_paper = Paper()

        self.clearBibData()
        self.clearOtherData()

        self.serializeMode()

        self.revise_button.config(state=DISABLED)
        self.del_button.config(state=DISABLED)
        self.find_button.config(state=NORMAL)
        self.add_button.config(state=NORMAL)
        self.bib_parser_button.config(state=NORMAL)
    
    def filterMode(self):
        self.clearBibData()
        self.clearOtherData()

        self.add_button.config(state=DISABLED)
        self.revise_button.config(state=DISABLED)
        self.del_button.config(state=DISABLED)
        self.find_button.config(state=NORMAL)
    
    def updateMode(self, paper_id):
        tree_id = self.paper_to_tree[paper_id]

        if paper_id in self.lib.papers:
            paper = self.lib.papers[paper_id]
            values = self.display_columns_values(paper)
            for i, col in enumerate(self.display_columns):
                self.display_papers.set(tree_id, column=col, value=values[i])
        else:
            self.display_papers.delete(tree_id)
            del self.paper_to_tree[paper_id]
        
        df_idx = self.display_filter.curselection()
        filtername = ''
        if len(df_idx) > 0:
            filtername = self.display_filter.get(df_idx)

        fc_idx = self.filter_category.current()
        self.setFilterCategory(fc_idx)

        displayed_filternames = self.display_filter.get(0, "end")
        if filtername in displayed_filternames:
            df_idx = displayed_filternames.index(filtername)
            self.setDisplayFilter(df_idx)

        self.serializeMode()
    
    def resetMode(self):
        self.cur_paper = Paper()

        self.clearBibData()
        self.clearOtherData()

        self.clearDisplayPapers()
        self.displayPaper(self.lib.papers)
        
        self.filter_category.current(0)
        self.clearFilter()

        self.revise_button.config(state=DISABLED)
        self.del_button.config(state=DISABLED)
        self.find_button.config(state=NORMAL)
        self.add_button.config(state=NORMAL)
        self.bib_parser_button.config(state=NORMAL)
    
    def serializeMode(self):
        self.serialize_button.config(state=NORMAL)
    
    def unserializeMode(self):
        self.serialize_button.config(state=DISABLED)
        
    # add, delete, find and revise

    def addPaper(self):
        self.cur_paper = self.collectInputData()

        if self.cur_paper.checkState() == 1:
            messagebox.showinfo(message='Wrong path!')
            return
        elif self.cur_paper.checkState() == 2:
            messagebox.showinfo(message='Please input at least title, author, conference, year!')
            return

        # search the title and path
        paper_id = self.lib.searchDuplicatePaper(self.cur_paper)

        if paper_id < 0:
            self.lib.addPaper(self.cur_paper)
            self.cur_paper._need_revise = False
            self.displayPaper([self.cur_paper.id])
            
            self.addMode()
        elif messagebox.askokcancel("Repeated File Error!","Do you want to browse the other file?") :
            self.resetMode()
            
            self.cur_paper = self.lib.papers[paper_id]
            self.display_papers.selection_set(self.paper_to_tree[paper_id])

    def delPaper(self):
        paper_id = self.cur_paper.id

        self.removed_files.append(self.cur_paper.full_path)
        self.lib.removePaper(paper_id)
        self.updateMode(paper_id)

        cur_trees = self.display_papers.get_children()
        if len(cur_trees) > 0:
            next_paper_treeid = cur_trees[0]
            self.cur_paper = self.lib.papers[self.display_papers.item(next_paper_treeid)['text']]
            self.display_papers.selection_set(next_paper_treeid)
        else:
            self.resetMode()
    
    # todo: first search on path, then other information
    def findPaper(self):
        self.cur_paper = Paper()
        self.cur_paper = self.collectInputData()

        paper_ids = self.lib.findPaper(self.cur_paper, target_paper_ids=self.paper_to_tree, support_fuzzy=True, fuzzy_window=2)

        if len(paper_ids) < 1:
            messagebox.showinfo(message='Find nothing!')
            return

        self.clearDisplayPapers()
        self.displayPaper(paper_ids)
    
    def revisePaper(self):
        target_paper_id = self.cur_paper.id

        self.cur_paper = self.collectInputData()

        depulated_pi = self.lib.searchDuplicatePaper(self.cur_paper)

        if self.cur_paper.checkState() == 1 or ( depulated_pi >= 0 and depulated_pi != target_paper_id):
            messagebox.showinfo(message='Wrong path or repeated path/title!')
            self.cur_paper = self.lib.papers[target_paper_id]
            return
        # not check bib info to support watch foler adding new paper
        elif self.cur_paper.checkState() == 2:
            messagebox.showinfo(message='Please input at least title, author, conference, year!')
            return

        if self.lib.revisePaper(target_paper_id, self.cur_paper):
            self.lib.papers[target_paper_id]._need_revise = False

            self.updateMode(target_paper_id)
            
            messagebox.showinfo(message='Revise paper data success!')
            if target_paper_id in self.paper_to_tree:
                tree_id = self.paper_to_tree[target_paper_id]
                self.cur_paper = self.lib.papers[target_paper_id]
                self.display_papers.selection_set(tree_id)
            else:
                cur_trees = self.display_papers.get_children()
                if len(cur_trees) > 0:
                    next_paper_treeid = cur_trees[0]
                    self.cur_paper = self.lib.papers[self.display_papers.item(next_paper_treeid)['text']]
                    self.display_papers.selection_set(next_paper_treeid)
                else:
                    self.resetMode()
        else:
            tree_id = self.paper_to_tree[target_paper_id]
            self.cur_paper = self.lib.papers[target_paper_id]
            self.display_papers.selection_set(tree_id)
    
    def parseBib(self):
        bib_str = self.add_bib_input.get(1.0, END).strip()
        if len(bib_str) > 0:
            b = bibParser.parse(bib_str, self.lib)
            self.displayBibData(b)

    def reparse(self):
        if messagebox.askokcancel("ReNewal","Do you want to re-Parse bibtex and path for all papers?") :
            # collect all papers' paths
            lib_files = {}
            existing_files = {}     # all files in the current folder

            same_files = {}     # different files share common filename

            new_files = set()
            to_be_corrected_files = set()

            for paper_id in self.lib.papers:
                paper = self.lib.papers[paper_id]
                lib_files[ntpath.basename(paper.path)] = paper_id
            
            for (dirpath, dirs, filenames) in os.walk(application_path):
                # skip hidden folders and files
                files = [f for f in filenames if not f[0] == '.' and f.endswith('.pdf')]
                dirs[:] = [d for d in dirs if not d[0] == '.']

                for filename in files:
                    tmp_full_path = os.path.join(dirpath, filename)
                    if filename not in existing_files:
                        existing_files[filename] = tmp_full_path

                        if filename not in lib_files :
                            new_files.add(filename)
                        elif tmp_full_path != self.lib.papers[lib_files[filename]].full_path :
                            to_be_corrected_files.add(filename)
                    else:
                        same_files[tmp_full_path] = filename
            
            nofile_lib_pis = set()
            for f in lib_files:
                if f not in existing_files:
                    nofile_lib_pis.add(lib_files[f])
                    self.lib.papers[lib_files[f]]._need_revise = True
            
            if len(same_files) > 0:
                # todo: custom dialog
                if messagebox.askokcancel("Reparse failed!","Do you want to delete the following repeated files or do it by yourself?\n\n"+"\n".join(["{}->{}".format(k, existing_files[same_files[k]]) for k in same_files])):
                    for f in same_files:
                        os.remove(f)
            else:
                revise_bib_count = 0
                for paper_id in self.lib.papers:
                    paper = self.lib.papers[paper_id]
                    # reparse bibtex
                    if len(paper.bib.bibtex) > 0 :
                        b = bibParser.parse(paper.bib.bibtex, self.lib)
                        if self.lib.revisePaperBib(paper_id, b) : revise_bib_count += 1

                # correct path
                for f in to_be_corrected_files:
                    self.lib.papers[lib_files[f]].path = os.path.relpath(existing_files[f], start=application_path)
                        
                self.resetMode()

                if len(nofile_lib_pis) + len(new_files)>0 and messagebox.askokcancel("Incorrect and New Files!", "Reparse success! {} bibtex and {} path!\n".format(revise_bib_count, len(to_be_corrected_files)) + 
                "Added {} new files!".format(len(new_files)) + 
                "Do you want to correct {} path and complete new files now?\n".format(len(nofile_lib_pis)) ):

                    # add new files
                    new_paths = [existing_files[filename] for filename in new_files]
                    self.importNewPapers(new_paths)

                    self.setFilter('others', 'needRevise')
                    self.serializeMode()
                else:
                    messagebox.showinfo(message="Reparse success! {} bibtex and {} path!\n".format(revise_bib_count, len(to_be_corrected_files)))
                    if revise_bib_count > 0 or len(to_be_corrected_files)>0:
                        self.serializeMode()
    
    def setFilter(self, filter_category, filtername):
        self.setFilterCategoryByName(filter_category)

        displayed_filternames = self.display_filter.get(0, "end")
        if filtername in displayed_filternames:
            filter_idx = displayed_filternames.index(filtername)
            self.setDisplayFilter(filter_idx)

    def setFilterCategory(self, idx):
        self.clearFilter()
        if idx != 0:
            if idx > 0 and idx <= len(self.filter_type_list):
                self.filter_category.current(idx)
            else: idx = self.filter_category.current()
            
            filtertype = self.filter_type_list[idx-1]
            filters = self.filter_dict[filtertype]

            for f in filters:
                self.display_filter.insert(END, f)
        else:
            self.resetMode()
    
    def setFilterCategoryByName(self, filter_category):
        if filter_category in self.filter_type_list:
            idx = self.filter_type_list.index(filter_category) + 1
        else : idx = 0
        self.setFilterCategory(idx)
        return idx
    
    def importNewPapers(self, new_files):
        new_paper_ids = set()
        for path in new_files:
            tmp_paper = Paper()
            tmp_paper.path = os.path.relpath(path, start=application_path)
            tmp_paper.title = self.extractTitleFromPath(tmp_paper.path)
            tmp_paper._need_revise = True
            # todo: what if there is duplicated papers
            depulated_pi = self.lib.searchDuplicatePaper(tmp_paper)
            if depulated_pi < 0:
                new_paper_ids.add(self.lib.addPaper(tmp_paper))
        return new_paper_ids

    
    def importFiles(self):
        # Ask the user to select multiple files
        path_list = filedialog.askopenfilenames(parent=self.root,
                                    initialdir=application_path,
                                    title="Please select files:",
                                    filetypes=my_filetypes)
        if len(path_list) > 0:
            self.importNewPapers(path_list)
            self.setFilter('others', 'needRevise')
            self.serializeMode()
                
    
    def browseFiles(self):
        # Ask the user to select a single file name.
        full_path = filedialog.askopenfilename(parent=self.root,
                                    initialdir=application_path,
                                    title="Please select a file:",
                                    filetypes=my_filetypes)

        if len(full_path) > 0:
            path = os.path.relpath(full_path, start=application_path)
            self.add_path_input.delete(0, 'end')
            self.add_path_input.insert(0, path)

            # update title if title is empty
            title = self.add_title_input.get().strip()
            if len(title) < 1:
                self.add_title_input.insert(0, self.extractTitleFromPath(full_path))

        return full_path
    
    def extractTitleFromPath(self, path):
        filename = ntpath.basename(path)
        title = filename
        for ft in filetypes:
            if filename.endswith(ft):
                title = filename[:-len(ft)]
        return title

    # todo: parse pdf ?
    def fetchGS(self):
        sufficient_info = True
        bibtex = ""

        tmp_bib = Bib()
        tmp_bib = self.collectBibData(tmp_bib)
        query_str = tmp_bib.shortString()

        if len(tmp_bib.title) < 1:
            tmp_path = self.add_path_input.get().strip()
            title = self.extractTitleFromPath(tmp_path)
            if len(title) < 1 :
                sufficient_info = False
            query_str = title + tmp_bib.shortString()

        if sufficient_info:
            result = bibParser.query(query_str)
            if len(result) > 0 :
                bibtex = result[0]

        if len(bibtex) > 0:
            self.add_bib_input.delete(1.0, END)
            self.add_bib_input.insert(1.0, bibtex)

            title = bibParser.titleParser(bibtex)
            if len(title) > 0:
                self.add_title_input.delete(0, 'end')
                self.add_title_input.insert(0, title)
            
            a_str = bibParser.authorParser(bibtex)
            if len(a_str) > 0:
                self.add_author_input.delete(0, 'end')
                self.add_author_input.insert(0, ';'.join(Author.parseAuthorString(a_str)))

            c_str = bibParser.conferenceParser(bibtex)
            if len(c_str) > 0:
                conference = self.lib.parseConference(c_str)
                self.add_conference.current(conference.index)
            
            y_str = bibParser.yearParser(bibtex)
            if len(y_str) > 0:
                self.spinval.set(int(y_str))
        else:
            messagebox.showinfo(message="Can't find it on Google Scholar, please fill in more data!\n")
    
    def clearBibtex(self):
        self.add_bib_input.delete(1.0, END)
    # event

    def closeWindow(self):
        if str(self.serialize_button['state']) == NORMAL and messagebox.askokcancel("Exit","Do you want to sync before exit?") :
            f = open(lib_file, 'wb')
            pickle_dump(self.lib, f)
        self.root.destroy()

    def filterListingEvent(self, event):
        filter_type = self.filter_category.get()
        
        self.setFilterCategoryByName(filter_type)
    
    def setProgress(self, cur_value, max_value):
        self.progress["maximum"] = max_value
        self.progress["value"] = cur_value
    
    def filteredPaperEvent(self, event):
        filter_idx = self.display_filter.curselection()
        if len(filter_idx) > 0:
            self.setDisplayFilter(filter_idx[0])

    def setDisplayFilter(self, idx):
        displayed_filternames = self.display_filter.get(0, "end")

        if idx >= 0 and idx < len(displayed_filternames):
            self.clearDisplayPapers()
            self.display_filter.selection_set(idx)

            item = self.display_filter.get(idx)
            filter_name = self.filter_category.get()

            paper_ids = set()
            if filter_name in self.filter_dict:
                filters = self.filter_dict[filter_name]
                if filter_name == 'year' or filter_name == 'rating':
                    paper_ids = filters[item]
                elif filter_name == 'others':
                    paper_ids = filters[item]()
                else:
                    paper_ids = filters[item].papers

            if len(paper_ids) > 0:
                self.displayPaper(paper_ids)

                treeid = self.display_papers.get_children()[0]
                self.cur_paper = self.lib.papers[self.display_papers.item(treeid)['text']]
                self.display_papers.selection_set(treeid)

                # show progress
                total_num = len(paper_ids)
                if total_num > 0:
                    unread_num = len( paper_ids & self.lib.findUnread())
                    self.setProgress(total_num-unread_num, total_num)
                self.filterMode()

    def selectPaperEvent(self, event):
        self.selectMode()
    
    def clickPaperEvent(self, event):
        tree_id = self.display_papers.focus()
        if len(tree_id) > 0:
            paper_id = self.display_papers.item(tree_id)['text']
            self.cur_paper = self.lib.papers[paper_id]
            self.selectMode()

    def openPaperEvent(self, event):
        self.clickPaperEvent(event)
        path = self.cur_paper.full_path
        self.openPaper(path)

    def openPaper(self, path):
        # os.system("open "+tmp_paper.full_path)
        
        if sys.platform.startswith('darwin'):       # Mac
            stdout = subp_call(('open', path))
        elif os.name == 'nt': # For Windows
            os.startfile(path)
        elif os.name == 'posix': # For Linux, Mac, etc.
            stdout = subp_popen(['xdg-open', path])
            #subprocess.call(('xdg-open', full_path))
    
    # collect data
    def collectInputData(self):
        # get info for cur paper
        tmp_paper = Paper()
        tmp_paper.bib = self.collectBibData(tmp_paper.bib)
        tmp_paper = self.collectOtherData(tmp_paper)
        return tmp_paper
    
    def collectBibData(self, bib):
        bib.title = self.add_title_input.get().strip()
        bib.year = self.add_year_input.get()

        bib.conference = self.lib.parseConference(self.add_conference.get())
        bib.author = self.lib.parseAuthors(self.add_author_input.get())

        input_bibtex = self.add_bib_input.get(1.0, END).strip()
        bib.bibtex = input_bibtex if len(input_bibtex) > 0 else bib.__repr__()
        bib.type = bibParser.typeParser(bib.bibtex)

        return bib
    
    def collectOtherData(self, paper):
        paper.tag = self.lib.parseTags(self.add_tag_input.get().strip())
        paper.project = self.lib.parseProjects(self.add_project_input.get().strip())
        paper.dataset = self.lib.parseDatasets(self.add_dataset_input.get().strip())

        paper.comment = self.add_comment_input.get(1.0, END).strip()

        paper.rating = self.add_rating_input.get()

        paper.path = self.add_path_input.get().strip()

        paper.hasRead = self.hasRead.get()
        paper.hasGithub = self.hasGithub.get()
        return paper
    
    # display data
    
    def displayPaper(self, paper_ids):
        for pi in paper_ids:
            tree_id = self.display_papers.insert('', 'end', text=pi, values=self.display_columns_values(self.lib.papers[pi]))
            self.paper_to_tree[pi] = tree_id

    def displayData(self, paper):
        self.displayBibData(paper.bib)
        self.displayOtherData(paper)
    
    def displayBibData(self, bib):
        self.clearBibData()
        
        self.add_bib_input.insert(1.0, bib.bibtex)
        self.add_title_input.insert(0, bib.title)
        self.add_author_input.insert(0, Author.guiString(bib.author))
        self.add_conference.current(bib.conference.index)
        self.spinval.set(bib.year)

    def displayOtherData(self, paper):
        self.clearOtherData()

        self.add_path_input.insert(0, paper.path)
        self.add_tag_input.insert(0, paper.tag)
        self.add_project_input.insert(0, paper.project)
        self.add_dataset_input.insert(0, paper.dataset)
        self.add_comment_input.insert(1.0, paper.comment)
        self.r_spinval.set(paper._rating)
        self.hasRead.set(paper.hasRead)
        self.hasGithub.set(paper.hasGithub)
    
    # clear data
    
    def clearDisplayPapers(self):
        self.paper_to_tree.clear()
        self.display_papers.delete(*self.display_papers.get_children())

    def clearFilter(self):
        self.display_filter.delete(0, END)
        self.setProgress(0,1)

    def clearBibData(self):
        self.add_bib_input.delete(1.0, END)
        self.add_title_input.delete(0, 'end')
        self.add_author_input.delete(0, 'end')
        self.add_conference.current(0)
        self.spinval.set(DEFAULT_YEAR)
    
    def clearOtherData(self):
        self.add_path_input.delete(0, 'end')
        self.add_tag_input.delete(0, 'end')
        self.add_project_input.delete(0, 'end')
        self.add_dataset_input.delete(0, 'end')
        self.add_comment_input.delete(1.0, END)
        self.r_spinval.set(0)

        self.hasGithub.set(False)
        self.hasRead.set(False)


def main():
    # instantiation
    lg = LibraryGUI()
    lg.init()
    lg.gui_arrang()
    # main program
    lg.root.mainloop()
    pass


if __name__ == "__main__":
    main()