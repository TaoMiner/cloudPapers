#!/usr/bin/env python3

from tkinter import *
from tkinter import messagebox
from tkinter import ttk
from tkinter import filedialog
import tkinter.font as tkfont
import os
import pickle
import subprocess
import re
import datetime

ROOTPATH = os.getcwd()
lib_file = "papers.dat"
conference_file = "./conference.dat"
DEFAULT_YEAR = 1900
MAX_RATING = 5
OTHERS_CONFERENCE = 'others'

# Build a list of tuples for each file type the file dialog should display
my_filetypes = [('all files', '.*'), ('pdf files', '.pdf'), ('text files', '.txt')]

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

type_re = re.compile(r'^@inproceedings(.*)')
title_re = re.compile(r'(?<=[^a-z]title\={).+?(?=})')
author_re = re.compile(r'(?<=[^a-z]author\={).+?(?=})')
conference_re = re.compile(r'(?<=[^a-z]booktitle\={).+?(?=})|(?<=[^a-z]journal\={).+?(?=})')
year_re = re.compile(r'(?<=[^a-z]year\={).+?(?=})')
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
        full_path = os.path.abspath(value)
        if os.path.isfile(full_path):
            self._path = os.path.relpath(full_path)

    @property
    def full_path(self):
        return os.path.abspath(self._path)

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
        self.data_file = os.path.abspath(lib_file)

        self._years = {}     # {year:set(paper_id, ...), ...}

        self._authors = {}   # author_label: Author()
        self._conferences = {OTHERS_CONFERENCE:Conference(OTHERS_CONFERENCE)}   # conference_label: Conference()
        self._datasets = {}   # dataset_label: Conference()
        self._tags = {}   # tag_label: Conference()
        self._projects = {}   # project_label: Conference()
        self._ratings = {}      # rating: set(paper_id, ...)

        self._papers = {}   # paper_id: Paper()
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
        if len(c_list) > 0:
            # todo: compute similarity and pick up the similarer one
            re_c = c_list[0]
            for c in c_list:
                if c_str == c.label:
                    re_c = c
        else: re_c = self.conferences[OTHERS_CONFERENCE]
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
    
    def addPaperYear(self, paper_id, year):
        tmp_paper_set = self._years.get(year, set())
        tmp_paper_set.add(paper_id)
        self._years[year] = tmp_paper_set
    
    def addPaperRating(self, paper_id, rating):
        tmp_paper_set = self._ratings.get(rating, set())
        tmp_paper_set.add(paper_id)
        self._ratings[rating] = tmp_paper_set
    
    def addPaperCategory(self, paper_id, categories, target_categories):
        for c in categories:
            if len(c.papers) == 0:
                target_categories[c.label] = c
            c.papers.add(paper_id)
    
    def revisePaperBib(self, paper_id, bib):
        target_paper = self.papers[paper_id]

        if target_paper.bibtex != bib.bibtex:
            target_paper.bib.bibtex = bib.bibtex

        if target_paper.papertype != bib.type:
            target_paper.bib.type = bib.type

        if target_paper.title != bib.title:
            target_paper.bib.title = bib.title
        
        if int(target_paper.year) != bib.year:
            self.years[target_paper.bib.year].remove(paper_id)
            if len(self.years[target_paper.bib.year]) == 0 :
                del self.years[target_paper.bib.year]
            self.addPaperYear(paper_id, bib.year)
            target_paper.bib.year = bib.year

        if target_paper.conference != bib.conference.label:
            target_paper.bib.conference.papers.remove(paper_id)
            target_paper.bib.conference = bib.conference
            bib.conference.papers.add(paper_id)

        if target_paper.author != Author.guiString(bib.author):
            target_paper.bib.author = self.revisePaperCategory(paper_id, bib.author, target_paper.bib.author, self.authors)
    
    def revisePaper(self, paper_id, paper):
        target_paper = self.papers[paper_id]

        if target_paper.path != paper.path:
            target_paper.path = paper.path

        self.revisePaperBib(paper_id, paper.bib)

        if target_paper.tag != paper.tag:
            target_paper._tag = self.revisePaperCategory(paper_id, paper._tag, target_paper._tag, self.tags)
        if target_paper.dataset != paper.dataset:
            target_paper._dataset = self.revisePaperCategory(paper_id, paper._dataset, target_paper._dataset, self.datasets)
        if target_paper.project != paper.project:
            target_paper._project = self.revisePaperCategory(paper_id, paper._project, target_paper._project, self.projects)

        if target_paper.comment != paper.comment:
            target_paper.comment = paper.comment
        
        if target_paper.hasRead != paper.hasRead:
            target_paper.hasRead = paper.hasRead
        if target_paper.hasGithub != paper.hasGithub:
            target_paper.hasGithub = paper.hasGithub
        
        if target_paper.rating != paper.rating:
            self.ratings[target_paper._rating].remove(paper_id)
            if len(self.ratings[target_paper._rating]) == 0:
                del self.ratings[target_paper._rating]
            self.addPaperRating(paper_id, paper._rating)
            target_paper._rating = paper._rating
    
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
        norm_path = os.path.normpath(paper.path)
        for pi in self.papers:
            if norm_path == self.papers[pi].path or paper.title == self.papers[pi].title:
                return pi
        return -1

    # todo: better fuzzy comment
    def findPaper(self, paper, support_fuzzy=False, fuzzy_window=0):
        
        title_papers = set()
        author_papers = set()
        conference_papers = set()
        year_papers = set()
        tag_papers = set()
        dataset_papers = set()
        project_papers = set()

        if len(paper.title) > 0:
            title_papers = self.findTitle(paper.title, support_fuzzy=support_fuzzy)

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

    def findTitle(self, t_str, support_fuzzy=False):
        papers = set()
        for pi in self._papers:
            if self.similarity(t_str, self._papers[pi].title, support_fuzzy=support_fuzzy):
                papers.add(pi)
        return papers
    
    def findConference(self, c_str, support_fuzzy=False):
        conferences = []
        if c_str != OTHERS_CONFERENCE:
            for conference_name in self._conferences:
                if c_str == conference_name or conference_name in c_str :
                    conferences.append(self._conferences[conference_name])
                elif support_fuzzy and self.similarity(c_str, conference_name, support_fuzzy=support_fuzzy):
                    conferences.append(self._conferences[conference_name])
        return conferences
    
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

class LibraryGUI:

    def __init__(self):
        self.lib = Library()
        self.cur_paper = Paper()
        self.paper_to_tree = {}
        self.authorize_conference_list = []

        self.display_columns = ('Title', 'Conference', 'Year', 'Read', 'Rating')
        self.display_columns_values = lambda x: (x.title, x.conference, x.year, 1 if x.hasRead else 0, x.rating)

        # gui style
        self.display_column_width = {'Title':300, 'Conference':100, 'Year':50, 'Read':50, 'Rating':50}
        self.fontSize = 14
        self.headFontSize = 12
        self.grid_width = 1

        # gui
        self.root = Tk()
        self.root.title("Cloud Paper Manager")
        self.root.resizable(width=False, height=False)
        self.pages = ttk.Notebook(self.root)

        # add and revise
        self.add_page = ttk.Frame(self.pages)

        self.display_papers = ttk.Treeview(self.add_page)  # lists of existing papers
        self.dp_yscroll = ttk.Scrollbar(self.add_page, command=self.display_papers.yview, orient=VERTICAL)
        self.display_papers.configure(yscrollcommand=self.dp_yscroll.set)

        # bibtex parser
        self.labelBibInput = ttk.Label(self.add_page, text='Bibtex:')
        self.add_bib_input = Text(self.add_page, height=5)
        self.add_bib_input.bind("<Tab>", self.focus_next_widget)
        self.bib_parser_button = ttk.Button(self.add_page, command = self.parseBib, text = "Parse")

        self.labelTitleInput = ttk.Label(self.add_page, text='Title:')
        self.add_title_input = ttk.Entry(self.add_page)

        self.labelAuthorInput = ttk.Label(self.add_page, text='Authors:')
        self.add_author_input = ttk.Entry(self.add_page)

        self.labelPathInput = ttk.Label(self.add_page, text='Path:')
        self.add_path_input = ttk.Entry(self.add_page)

        self.path_button = ttk.Button(self.add_page, command = self.browseFiles, text = "...")

        self.labelTagInput = ttk.Label(self.add_page, text='Tags:')
        self.add_tag_input = ttk.Entry(self.add_page)

        self.labelProjectInput = ttk.Label(self.add_page, text='Projects:')
        self.add_project_input = ttk.Entry(self.add_page)

        self.labelDatasetInput = ttk.Label(self.add_page, text='Datasets:')
        self.add_dataset_input = ttk.Entry(self.add_page)

        self.labelCommentInput = ttk.Label(self.add_page, text='Comments:')
        self.add_comment_input = Text(self.add_page, height=5)
        self.add_comment_input.bind("<Tab>", self.focus_next_widget)

        self.labelConferenceInput = ttk.Label(self.add_page, text='Conference:')
        conferences = StringVar()
        self.add_conference = ttk.Combobox(self.add_page, textvariable=conferences, width=2*self.grid_width)
        
        self.labelYearInput = ttk.Label(self.add_page, text='Year:')
        self.spinval = StringVar()
        self.add_year_input = Spinbox(self.add_page, from_=DEFAULT_YEAR, to=datetime.datetime.now().year, textvariable=self.spinval, width=self.grid_width)

        self.labelRatingInput = ttk.Label(self.add_page, text='Rating:')
        self.r_spinval = StringVar()
        self.add_rating_input = Spinbox(self.add_page, from_=0, to=MAX_RATING, textvariable=self.r_spinval, width=self.grid_width)

        self.hasRead = BooleanVar()
        self.read_check = ttk.Checkbutton(self.add_page, text='Read', variable=self.hasRead,
	    onvalue=True, offvalue=False)

        self.hasGithub = BooleanVar()
        self.github_check = ttk.Checkbutton(self.add_page, text='Github', variable=self.hasGithub,
	    onvalue=True, offvalue=False)

        self.add_button = ttk.Button(self.add_page, command = self.addPaper, text = "Add")
        self.del_button = ttk.Button(self.add_page, command = self.delPaper, text = "Remove")
        self.revise_button = ttk.Button(self.add_page, command = self.revisePaper, text = "Revise")
        self.find_button = ttk.Button(self.add_page, command = self.findPaper, text = "Find")

        self.reset_button = ttk.Button(self.add_page, command = self.resetMode, text = "Reset")
        self.serialize_button = ttk.Button(self.add_page, command = self.serialize, text = "Sync")

        self.reparse_button = ttk.Button(self.add_page, command = self.reparse, text = "RedoALL")

        self.bib_separator = ttk.Separator(self.add_page, orient=HORIZONTAL)
        self.data_separator = ttk.Separator(self.add_page, orient=HORIZONTAL)

        # present
        self.present_page = ttk.Frame(self.pages)

        self.labelCategoryInput = ttk.Label(self.present_page, text='FilterBy:')
        categories = StringVar()
        self.filter_category = ttk.Combobox(self.present_page, textvariable=categories, width=10)

        self.display_filter = Listbox(self.present_page, height=5)  # lists of existing filters
        self.df_yscroll = ttk.Scrollbar(self.present_page, command=self.display_filter.yview, orient=VERTICAL)
        self.display_filter.configure(yscrollcommand=self.df_yscroll.set)

        self.display_category_papers = ttk.Treeview(self.present_page)  # lists of filtered papers

        self.progress = ttk.Progressbar(self.present_page, orient=HORIZONTAL, length=200, mode='determinate')

        # add pages
        self.pages.add(self.add_page, text="Add")
        self.pages.add(self.present_page, text="Present")

    def focus_next_widget(self, event):
        event.widget.tk_focusNext().focus()
        return("break")

    def init(self):
        self.initLib()
        self.initConference(conference_file)
        self.initPresentPage()
        self.initAddPage()
        self.initButtons()
        self.initStyle()
    
    def initStyle(self):
        # font
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(size=self.fontSize)

        text_font = tkfont.nametofont('TkTextFont')
        text_font.configure(size=self.fontSize)

        text_font = tkfont.nametofont('TkFixedFont')
        text_font.configure(size=self.fontSize)

        text_font = tkfont.nametofont('TkHeadingFont')
        text_font.configure(size=self.headFontSize)
        # color
        # bg = self.add_page['bg']
        # self.labelBibInput.config(bg=bg)

    
    def initLib(self):
        # load existing papers
        self.deserialize()
        for p in self.lib.papers:
            tree_id = self.displayPaper(p, self.display_papers)
            self.paper_to_tree[p] = tree_id
    
    def initPresentPage(self):
        self.filter_dict = {'conference':self.lib.conferences, 'year':self.lib.years, 'author':self.lib.authors, 'dataset':self.lib.datasets, 'tag':self.lib.tags, 'project':self.lib.projects, 'rating':self.lib.ratings}
        self.filter_category['value'] = ['please select'] + list(self.filter_dict.keys()) + ['others']
        self.filter_category['state'] = "readonly"
        self.filter_category.current(0)
        self.filter_category.bind('<<ComboboxSelected>>', self.filterListingEvent)

        self.display_filter.bind("<<ListboxSelect>>", self.filteredPaperEvent)
        
        self.display_category_papers['columns'] = self.display_columns
        #hide #0 column for id
        self.display_category_papers['show'] = 'headings'
        # sort column
        for col in self.display_columns:
            self.display_category_papers.heading(col, text=col, command=lambda _col=col: \
                     self.treeview_sort_column(self.display_category_papers, _col, False))
            self.display_category_papers.column(col, width=self.display_column_width[col], anchor='center')
        self.display_category_papers.bind("<Double-1>", self.openCategoryPaperEvent)

    def initAddPage(self):
        self.display_papers['columns'] = self.display_columns
        # self.display_papers.heading('#0', text='Title')
        # hide #0 column
        self.display_papers['show'] = 'headings'
        # sort column
        for col in self.display_columns:
            self.display_papers.heading(col, text=col, command=lambda _col=col: \
                     self.treeview_sort_column(self.display_papers, _col, False))
            self.display_papers.column(col, width=self.display_column_width[col], anchor='center')

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
            if c_map[c_str] in self.lib.conferences and c_map[c_str] != self.lib.conferences[c_map[c_str]].label :
                self.lib.conferences[c_map[c_str]].label = c_map[c_str]
            elif c_map[c_str] not in self.lib.conferences:
                self.lib.conferences[c_map[c_str]] = Conference(c_map[c_str])

            if c_str in self.lib.conferences and c_map[c_str] != self.lib.conferences[c_str].label :
                self.lib.conferences[c_str].label = c_map[c_str]
            elif c_str not in self.lib.conferences:
                self.lib.conferences[c_str] = self.lib.conferences[c_map[c_str]]

        if OTHERS_CONFERENCE not in self.lib.conferences:
            self.lib.conferences[OTHERS_CONFERENCE] = Conference(OTHERS_CONFERENCE)
        
        for c_str in self.lib.conferences:
            if c_str == self.lib.conferences[c_str].label:
                self.authorize_conference_list.append(c_str)
                self.lib.conferences[c_str].index = len(self.authorize_conference_list)

    # finish gui arrange
    def gui_arrang(self):
        self.pages.grid()
        # present page
        # self.labelCategoryInput.grid(row=0, column=0, sticky=E)
        # self.filter_category.grid(row=0, column=1, sticky=(W,E))
        # self.progress.grid(row=0, column=3, sticky=W)

        # self.display_filter.grid(row=1, column=0, columnspan=2, rowspan=14, sticky=(N,W,E,S))
        # self.df_yscroll.grid(row=1, column=2, rowspan=14, sticky=(N,W,S))
        # self.display_category_papers.grid(row=1, column=3, columnspan=8, rowspan=14, sticky=(N,W,E,S))

        # add page 7 columns, 15 rows
        # self.add_page.grid_propagate(0)

        # main display paper table
        self.display_papers.grid(row=0, column=0, columnspan=4, rowspan=15, sticky=(N,W,E,S))
        self.dp_yscroll.grid(row=0, column=5, rowspan=15, sticky=(N,S))

        # global buttons

        self.reset_button.grid(row=0,column=8, sticky=(W,E))
        self.serialize_button.grid(row=0,column=9, sticky=(W,E))
        self.reparse_button.grid(row=0, column=10, sticky=(W,E))

        # self.data_separator.grid(row=1, column=2, columnspan=4, sticky=(N, W, E))

        # paper bib data

        self.labelBibInput.grid(row=1, column=6, sticky=(N,E))
        self.add_bib_input.grid(row=1, column=7, columnspan=4, rowspan=2, sticky=(W,E))
        self.bib_parser_button.grid(row=3, column=10, sticky=(W,E))

        self.labelTitleInput.grid(row=4,column=6, sticky=E)
        self.add_title_input.grid(row=4,column=7, columnspan=4, sticky=(W,E))

        self.labelAuthorInput.grid(row=5,column=6, sticky=E)
        self.add_author_input.grid(row=5,column=7, columnspan=4, sticky=(W,E))

        self.labelConferenceInput.grid(row=6,column=6, sticky=E)
        self.add_conference.grid(row=6,column=7, columnspan=2, sticky=(W,E))

        self.labelYearInput.grid(row=6,column=9, sticky=E)
        self.add_year_input.grid(row=6,column=10, sticky=(W,E))
        
        self.labelPathInput.grid(row=7,column=6, sticky=E)
        self.add_path_input.grid(row=7,column=7, columnspan=3, sticky=(W,E))
        self.path_button.grid(row=7, column=10, sticky=(W,E))

        self.bib_separator.grid(row=8, column=6, columnspan=5, sticky=(N, W, E))

        # paper optional data

        self.labelTagInput.grid(row=9,column=6, sticky=E)
        self.add_tag_input.grid(row=9,column=7, columnspan=4, sticky=(W,E))

        self.labelProjectInput.grid(row=10,column=6, sticky=E)
        self.add_project_input.grid(row=10,column=7, columnspan=4, sticky=(W,E))

        self.labelDatasetInput.grid(row=11,column=6, sticky=E)
        self.add_dataset_input.grid(row=11,column=7, columnspan=4, sticky=(W,E))

        self.labelCommentInput.grid(row=12,column=6, sticky=(N,E))
        self.add_comment_input.grid(row=12,column=7, columnspan=4, sticky=(W,E))

        self.labelRatingInput.grid(row=13,column=6, sticky=E)
        self.add_rating_input.grid(row=13,column=7, sticky=(W,E))

        self.read_check.grid(row=13,column=9, sticky=(W,E))
        self.github_check.grid(row=13,column=10, sticky=(W,E))

        self.add_button.grid(row=14,column=7, sticky=(W,E))
        self.revise_button.grid(row=14,column=8, sticky=(W,E))
        self.find_button.grid(row=14,column=9, sticky=(W,E))
        self.del_button.grid(row=14,column=10, sticky=(W,E))
    
    def serialize(self):
        f = open(lib_file, 'wb')
        pickle.dump(self.lib, f)
        messagebox.showinfo(message='Save lib data success!')
        self.unserializeMode()
    
    def deserialize(self):
        if os.path.isfile(lib_file):
            f = open(lib_file, 'rb')
            self.lib = pickle.load(f)

    # main modes
    
    def selectMode(self, paper_id):
        self.cur_paper = self.lib.papers[paper_id]

        self.displayData(self.cur_paper)

        self.add_button.config(state=DISABLED)
        self.find_button.config(state=DISABLED)
        self.del_button.config(state=NORMAL)
        self.revise_button.config(state=NORMAL)
    
    def addMode(self):
        self.resetMode()
        self.serializeMode()
    
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

        self.filterListing()
        self.clearCategoryPapers()

        self.serializeMode()
    
    def resetMode(self):
        # add page
        self.cur_paper = Paper()

        self.clearBibData()
        self.clearOtherData()

        self.paper_to_tree.clear()
        self.clearDisplayPapers()
        for pi in self.lib.papers:
            tree_id = self.displayPaper(pi, self.display_papers)
            self.paper_to_tree[pi] = tree_id

        # present page
        self.filter_category.current(0)
        self.clearFilter()
        self.clearCategoryPapers()

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
            tree_id = self.displayPaper(self.cur_paper.id, self.display_papers)
            self.paper_to_tree[self.cur_paper.id] = tree_id
            self.addMode()
        elif messagebox.askokcancel("Repeated File Error!","Do you want to browse the other file?") :
            self.display_papers.selection_set(self.paper_to_tree[paper_id])
            self.selectMode(paper_id)

    def delPaper(self):
        paper_id = self.cur_paper.id
        self.lib.removePaper(paper_id)
        self.updateMode(paper_id)
        self.addMode()
    
    def findPaper(self):
        self.cur_paper = Paper()
        self.cur_paper = self.collectInputData()

        self.display_papers.delete(*self.display_papers.get_children())
        paper_ids = self.lib.findPaper(self.cur_paper, support_fuzzy=True, fuzzy_window=2)
        for pi in paper_ids:
            self.displayPaper(pi, self.display_papers)
    
    def revisePaper(self):
        target_paper_id = self.cur_paper.id

        self.cur_paper = self.collectInputData()

        if self.cur_paper.checkState() == 1:
            messagebox.showinfo(message='Wrong path!')
            return
        elif self.cur_paper.checkState() == 2:
            messagebox.showinfo(message='Please input at least title, author, conference, year!')
            return

        self.lib.revisePaper(target_paper_id, self.cur_paper)
        
        messagebox.showinfo(message='Revise paper data success!')
        self.selectMode(target_paper_id)
        self.updateMode(target_paper_id)
    
    def parseBib(self):
        bib_str = self.add_bib_input.get(1.0, END).strip()
        b = bibParser.parse(bib_str, self.lib)
        self.displayBibData(b)

    def reparse(self):
        for paper_id in self.lib.papers:
            paper = self.lib.papers[paper_id]
            if len(paper.bib.bibtex) > 0 :
                b = bibParser.parse(paper.bib.bibtex, self.lib)
                self.lib.revisePaperBib(paper_id, b)

                self.updateMode(paper_id)
        messagebox.showinfo(message="Reparse each paper's bibtex success!")
    
    def browseFiles(self):
        # Ask the user to select a single file name.
        full_path = filedialog.askopenfilename(parent=self.add_page,
                                    initialdir=os.getcwd(),
                                    title="Please select a file:",
                                    filetypes=my_filetypes)
        if len(full_path) > 0:
            path = os.path.relpath(full_path)
            self.add_path_input.delete(0, 'end')
            self.add_path_input.insert(0, path)
            self.openPaper(full_path)
    
    # event

    def filterListingEvent(self, event):
        self.filterListing()

    def filterListing(self):
        self.clearFilter()
        self.clearCategoryPapers()
        filter_name = self.filter_category.get()
        
        if filter_name in self.filter_dict:
            filters = self.filter_dict[filter_name]
            if filter_name == 'year' or filter_name == 'rating':
                for f in filters:
                    self.display_filter.insert(END, f)
            elif filter_name == 'conference':
                for f in filters:
                    if f == filters[f].label:
                        self.display_filter.insert(END, f)
            else:
                for f in filters:
                    self.display_filter.insert(END, f)
        elif filter_name == 'others':
            self.display_filter.insert(END, 'UnRead')
            self.display_filter.insert(END, 'hasGithub')

    def selectItem(self, paper_tree):
        curItem = paper_tree.focus()
        return paper_tree.item(curItem)['text']
    
    def setProgress(self, cur_value, max_value):
        self.progress["maximum"] = max_value
        self.progress["value"] = cur_value
    
    def filteredPaperEvent(self, event):
        self.filteredPaper()

    def filteredPaper(self):
        self.clearCategoryPapers()

        idx = self.display_filter.curselection()
        if idx is not None and len(idx) > 0:
            item = self.display_filter.get(idx)
            
            filter_name = self.filter_category.get()

            paper_ids = set()
            if filter_name in self.filter_dict:
                if filter_name == 'year':
                    paper_ids = self.lib.years[item]
                elif filter_name == 'rating':
                    paper_ids = self.lib.ratings[item]
                elif filter_name == 'conference':
                    paper_ids = self.lib.conferences[item].papers
                elif filter_name == 'author':
                    paper_ids = self.lib.authors[item].papers
                elif filter_name == 'tag':
                    paper_ids = self.lib.tags[item].papers
                elif filter_name == 'dataset':
                    paper_ids = self.lib.datasets[item].papers
                elif filter_name == 'project':
                    paper_ids = self.lib.projects[item].papers
            elif filter_name == 'others':
                if item == 'UnRead':
                    paper_ids = self.lib.findUnread()
                else:
                    paper_ids = self.lib.findGithub()

            for pi in paper_ids:
                self.displayPaper(pi, self.display_category_papers)

            # show progress
            total_num = len(paper_ids)
            if total_num > 0:
                unread_num = len( paper_ids & self.lib.findUnread())
                self.setProgress(total_num-unread_num, total_num)
    
    def openCategoryPaperEvent(self, event):
        self.openCategoryPaper()

    def openCategoryPaper(self):
        paper_id = self.selectItem(self.display_category_papers)
        self.pages.select(self.add_page)

        self.selectMode(paper_id)

    def selectPaperEvent(self, event):
        paper_id = self.selectItem(self.display_papers)
        self.selectMode(paper_id)
        return True

    def openPaperEvent(self, event):
        selected = self.selectPaperEvent(event)
        if selected:
            path = self.cur_paper.full_path
            self.openPaper(path)

    def openPaper(self, path):
        # os.system("open "+tmp_paper.full_path)
        full_path = os.path.abspath(path)
        if sys.platform.startswith('darwin'):
            subprocess.call(('open', full_path))
        elif os.name == 'nt': # For Windows
            os.startfile(full_path)
        elif os.name == 'posix': # For Linux, Mac, etc.
            subprocess.call(('xdg-open', full_path))
    
    # collect data
    def collectInputData(self):
        # get info for cur paper
        tmp_paper = Paper()
        tmp_paper = self.collectBibData(tmp_paper)
        tmp_paper = self.collectOtherData(tmp_paper)
        return tmp_paper
    
    def collectBibData(self, paper):
        paper.bibtex = self.add_bib_input.get(1.0, END).strip()
        paper.type = bibParser.typeParser(paper.bibtex)
        paper.title = self.add_title_input.get().strip()
        paper.year = self.add_year_input.get()

        paper.conference = self.lib.parseConference(self.add_conference.get())
        paper.author = self.lib.parseAuthors(self.add_author_input.get())
        return paper
    
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
    
    def displayPaper(self, paper_id, tree_widget):
        tmp_paper = self.lib.papers[paper_id]
        tree_id = tree_widget.insert('', 'end', text=paper_id, values=self.display_columns_values(tmp_paper))
        return tree_id

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
        self.display_papers.delete(*self.display_papers.get_children())

    def clearFilter(self):
        self.display_filter.delete(0, END)

    def clearCategoryPapers(self):
        self.display_category_papers.delete(*self.display_category_papers.get_children())

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