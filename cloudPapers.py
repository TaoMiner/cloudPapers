from tkinter import *
from tkinter import messagebox
from tkinter import ttk
import os
import pickle
import subprocess
import re
import datetime

ROOTPATH = os.getcwd()
lib_file = "./papers.dat"
conference_file = "./conference.dat"
DEFAULT_YEAR = 1900
OTHERS_CONFERENCE = 'others'

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
                items = line.strip().lower().split('\t')
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
        return "@inproceedings{{{},\n  title={{{}}},\n  author={{{}}},\n  booktitle={{{}}},\n  year={{{}}}\n}}".format(tmp_cite, self.title, Author.bibString(self.author), self.conference.label, str(self.year))

title_re = re.compile(r'(?<=[^a-z]title\={).+?(?=})')
author_re = re.compile(r'(?<=[^a-z]author\={).+?(?=})')
conference_re = re.compile(r'(?<=[^a-z]booktitle\={).+?(?=})')
year_re = re.compile(r'(?<=[^a-z]year\={).+?(?=})')
class bibParser:

    @classmethod
    def parse(cls, bib_str, lib=None):
        b = Bib()
        b.title = cls.titleParser(bib_str)
        b.author = cls.authorParser(bib_str, lib=lib)
        b.conference = cls.conferenceParser(bib_str, lib=lib)
        b.year = cls.yearParser(bib_str)
        return b
    
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
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = ""
        full_path = os.path.join(ROOTPATH, value)
        if os.path.isfile(full_path):
            self._path = os.path.normpath(value)

    @property
    def full_path(self):
        return os.path.join(ROOTPATH, self._path)

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
        state = True
        if self.title == "" or self.author == "" or self.conference == "" or self.year == "" :
            state = False
        if self._path == "" :
            state = False
        return state

class Library:
    def __init__(self):
        self.data_file = os.path.join(ROOTPATH, lib_file)

        self._years = {}     # {year:set(paper_id, ...), ...}

        self._authors = {}   # author_label: Author()
        self._conferences = {OTHERS_CONFERENCE:Conference(OTHERS_CONFERENCE)}   # conference_label: Conference()
        self._datasets = {}   # dataset_label: Conference()
        self._tags = {}   # tag_label: Conference()
        self._projects = {}   # project_label: Conference()

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

            del self._papers[paper_id]
            self.paper_id_pool.add(paper_id)
    
    # paper: Paper()
    def addPaper(self, paper):
        
        paper_id = self.generatePaperId()
        paper.id = paper_id

        self.addPaperYear(paper_id, paper.bib.year)

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
    
    def addPaperCategory(self, paper_id, categories, target_categories):
        for c in categories:
            if len(c.papers) == 0:
                target_categories[c.label] = c
            c.papers.add(paper_id)
    
    def revisePaper(self, paper_id, paper):
        target_paper = self.papers[paper_id]

        if target_paper.path != paper.path:
            target_paper.path = paper.path
            if target_paper.path != paper.path:
                return True

        if target_paper.title != paper.title:
            target_paper.bib.title = paper.bib.title
        
        if target_paper.year != paper.year:
            target_paper.bib.year = paper.bib.year

        if target_paper.conference != paper.conference:
            target_paper.bib.conference.papers.remove(paper_id)
            target_paper.bib.conference = paper.bib.conference

        if target_paper.author != paper.author:
            target_paper.bib.author = self.revisePaperCategory(paper_id, paper.bib.author, target_paper.bib.author, self.authors)
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

        return False
    
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
    
    def searchDuplicatePaper(self, path):
        norm_path = os.path.normpath(path)
        for pi in self.papers:
            if norm_path == self.papers[pi].path:
                return pi
        return -1

    # todo: support fuzzy and comment
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

        # gui
        self.root = Tk()
        self.root.title("Cloud Paper Manager")
        self.pages = ttk.Notebook(self.root)

        # add and revise
        self.add_page = ttk.Frame(self.pages)

        self.display_papers = ttk.Treeview(self.add_page)  # lists of existing papers

        # bibtex parser
        labelBib=StringVar()
        labelBib.set("Bibtex:")
        self.labelBibInput = Label(self.add_page, textvariable=labelBib)
        self.add_bib_input = Text(self.add_page, width=55, height=5)
        self.add_bib_input.bind("<Tab>", self.focus_next_widget)
        self.bib_parser_button = Button(self.add_page, command = self.parseBib, text = "Parse")

        labelTitle=StringVar()
        labelTitle.set("Title:")
        self.labelTitleInput = Label(self.add_page, textvariable=labelTitle)
        self.add_title_input = Entry(self.add_page, width=35)

        labelAuthor = StringVar()
        labelAuthor.set("Authors:")
        self.labelAuthorInput = Label(self.add_page, textvariable=labelAuthor)
        self.add_author_input = Entry(self.add_page, width=35)

        labelPath = StringVar()
        labelPath.set("Path:")
        self.labelPathInput = Label(self.add_page, textvariable=labelPath)
        self.add_path_input = Entry(self.add_page, width=35)

        labelTag = StringVar()
        labelTag.set("Tags:")
        self.labelTagInput = Label(self.add_page, textvariable=labelTag)
        self.add_tag_input = Entry(self.add_page, width=35)

        labelProject = StringVar()
        labelProject.set("Projects:")
        self.labelProjectInput = Label(self.add_page, textvariable=labelProject)
        self.add_project_input = Entry(self.add_page, width=35)

        labelDataset = StringVar()
        labelDataset.set("Datasets:")
        self.labelDatasetInput = Label(self.add_page, textvariable=labelDataset)
        self.add_dataset_input = Entry(self.add_page, width=35)

        labelComment = StringVar()
        labelComment.set("Comments:")
        self.labelCommentInput = Label(self.add_page, textvariable=labelComment)
        self.add_comment_input = Text(self.add_page, width=35, height=5)
        self.add_comment_input.bind("<Tab>", self.focus_next_widget)

        labelConference = StringVar()
        labelConference.set("Conference:")
        self.labelConferenceInput = Label(self.add_page, textvariable=labelConference)
        conferences = StringVar()
        self.add_conference = ttk.Combobox(self.add_page, textvariable=conferences)
        
        labelYear = StringVar()
        labelYear.set("Year:")
        self.labelYearInput = Label(self.add_page, textvariable=labelYear)
        self.spinval = StringVar()
        self.add_year_input = Spinbox(self.add_page, from_=DEFAULT_YEAR, to=datetime.datetime.now().year, textvariable=self.spinval)

        self.hasRead = BooleanVar()
        self.read_check = ttk.Checkbutton(self.add_page, text='Read', variable=self.hasRead,
	    onvalue=True, offvalue=False)

        self.hasGithub = BooleanVar()
        self.github_check = ttk.Checkbutton(self.add_page, text='Github', variable=self.hasGithub,
	    onvalue=True, offvalue=False)

        self.add_button = Button(self.add_page, command = self.addPaper, text = "Add")
        self.del_button = Button(self.add_page, command = self.delPaper, text = "Remove")
        self.revise_button = Button(self.add_page, command = self.revisePaper, text = "Revise")
        self.find_button = Button(self.add_page, command = self.findPaper, text = "Find")

        self.reset_button = Button(self.add_page, command = self.resetMode, text = "Reset")
        self.serialize_button = Button(self.add_page, command = self.serialize, text = "Sync")

        # present
        self.present_page = ttk.Frame(self.pages)

        labelCategory = StringVar()
        labelCategory.set("FilterBy:")
        self.labelCategoryInput = Label(self.present_page, textvariable=labelCategory)
        categories = StringVar()
        self.filter_category = ttk.Combobox(self.present_page, textvariable=categories)

        self.display_filter = ttk.Treeview(self.present_page)  # lists of existing filters

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
    
    def initLib(self):
        # load existing papers
        self.deserialize()
        for p in self.lib.papers:
            tree_id = self.displayPaper(p, self.display_papers)
            self.paper_to_tree[p] = tree_id
    
    def initPresentPage(self):
        self.filter_dict = {'conference':self.lib.conferences, 'year':self.lib.years, 'author':self.lib.authors, 'dataset':self.lib.datasets, 'tag':self.lib.tags, 'project':self.lib.projects}
        self.filter_category['value'] = ['please select'] + list(self.filter_dict.keys()) + ['others']
        self.filter_category['state'] = "readonly"
        self.filter_category.current(0)
        self.filter_category.bind('<<ComboboxSelected>>', self.filterListingEvent)

        self.display_filter.heading('#0', text='Filter')
        self.display_filter.bind("<<TreeviewSelect>>", self.filteredPaperEvent)
        
        self.display_category_papers['columns'] = ('title', 'conference', 'year')
        self.display_category_papers['show'] = 'headings'
        # self.display_papers.heading('#0', text='Title')
        self.display_category_papers.heading('title', text='Title')
        self.display_category_papers.heading('conference', text='Conference')
        self.display_category_papers.heading('year', text='Year')
        self.display_category_papers.bind("<Double-1>", self.openCategoryPaperEvent)

    def initAddPage(self):
        self.display_papers['columns'] = ('title', 'conference', 'year')
        # self.display_papers.heading('#0', text='Title')
        self.display_papers['show'] = 'headings'
        self.display_papers.heading('title', text='Title')
        self.display_papers.heading('conference', text='Conference')
        self.display_papers.heading('year', text='Year')
        self.display_papers.bind("<<TreeviewSelect>>", self.selectPaperEvent)
        self.display_papers.bind("<Double-1>", self.openPaperEvent)

        # generate conference combobox
        self.add_conference['value'] = ['please select'] + self.authorize_conference_list
        self.add_conference['state'] = "readonly"
        self.add_conference.current(0)
    
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
        self.labelCategoryInput.grid(row=0, column=0)
        self.filter_category.grid(row=1, column=0)
        self.display_filter.grid(row=2, column=0)
        self.display_category_papers.grid(row=2, column=1)
        self.progress.grid(row=1, column=1)

        # add page
        self.display_papers.grid(row=0, column=0, rowspan=13)

        self.labelBibInput.grid(row=0, column=1)
        self.bib_parser_button.grid(row=0, column=2)
        self.reset_button.grid(row=0,column=3)
        self.serialize_button.grid(row=0,column=4)
        self.add_bib_input.grid(row=1, column=1, columnspan=4)

        self.labelTitleInput.grid(row=2,column=1)
        self.add_title_input.grid(row=2,column=2, columnspan=3)

        self.labelAuthorInput.grid(row=3,column=1)
        self.add_author_input.grid(row=3,column=2, columnspan=3)
        
        self.labelPathInput.grid(row=4,column=1)
        self.add_path_input.grid(row=4,column=2, columnspan=3)

        self.labelTagInput.grid(row=5,column=1)
        self.add_tag_input.grid(row=5,column=2, columnspan=3)

        self.labelProjectInput.grid(row=6,column=1)
        self.add_project_input.grid(row=6,column=2, columnspan=3)

        self.labelDatasetInput.grid(row=7,column=1)
        self.add_dataset_input.grid(row=7,column=2, columnspan=3)

        self.labelCommentInput.grid(row=8,column=1)
        self.add_comment_input.grid(row=8,column=2, columnspan=3)
        
        self.labelConferenceInput.grid(row=9,column=1)
        self.add_conference.grid(row=9,column=2, columnspan=3)

        self.labelYearInput.grid(row=10,column=1)
        self.add_year_input.grid(row=10,column=2, columnspan=3)

        self.read_check.grid(row=11,column=1,columnspan=2)
        self.github_check.grid(row=11,column=3,columnspan=2)

        self.add_button.grid(row=12,column=1)
        self.revise_button.grid(row=12,column=2)
        self.find_button.grid(row=12,column=3)
        self.del_button.grid(row=12,column=4)
    
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

        self.displayData(self.lib.papers[paper_id])

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
            self.display_papers.set(tree_id, column='title', value=paper.title)
            self.display_papers.set(tree_id, column='conference', value=paper.conference)
            self.display_papers.set(tree_id, column='year', value=paper.year)
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

        if not self.cur_paper.checkState():
            messagebox.showinfo(message='Please input at least title, author, conference, year and path!')
            return

        paper_id = self.lib.searchDuplicatePaper(self.cur_paper.path)

        if paper_id < 0:
            self.lib.addPaper(self.cur_paper)
            tree_id = self.displayPaper(self.cur_paper.id, self.display_papers)
            self.paper_to_tree[self.cur_paper.id] = tree_id
            self.addMode()
        else:
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

        err = self.lib.revisePaper(target_paper_id, self.cur_paper)
        
        if not err:
            messagebox.showinfo(message='Revise paper data success!')
            self.selectMode(target_paper_id)
            self.updateMode(target_paper_id)
        else:
            self.cur_paper = self.lib.papers[target_paper_id]
            messagebox.showinfo(message='File path not exists!')
    
    def parseBib(self):
        bib_str = self.add_bib_input.get(1.0, END)
        b = bibParser.parse(bib_str, self.lib)
        self.displayBibData(b)
    
    # event

    def filterListingEvent(self, event):
        self.filterListing()

    def filterListing(self):
        self.clearFilter()
        self.clearCategoryPapers()

        filter_name = self.filter_category.get()
        
        if filter_name in self.filter_dict:
            filters = self.filter_dict[filter_name]
            if filter_name == 'year':
                for f in filters:
                    self.display_filter.insert('', 'end', text=f)
            elif filter_name == 'conference':
                for f in filters:
                    if f == filters[f].label:
                        self.display_filter.insert('', 'end', text=f)
            else:
                for f in filters:
                    self.display_filter.insert('', 'end', text=f)
        elif filter_name == 'others':
            self.display_filter.insert('', 'end', text='UnRead')
            self.display_filter.insert('', 'end', text='hasGithub')

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

        item = self.selectItem(self.display_filter)
        
        filter_name = self.filter_category.get()

        paper_ids = set()
        if filter_name in self.filter_dict:
            if filter_name == 'year':
                paper_ids = self.lib.years[item]
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
        if sys.platform.startswith('darwin'):
            subprocess.call(('open', path))
        elif os.name == 'nt': # For Windows
            os.startfile(path)
        elif os.name == 'posix': # For Linux, Mac, etc.
            subprocess.call(('xdg-open', path))
    
    # collect data
    def collectInputData(self):
        # get info for cur paper
        tmp_paper = Paper()
        tmp_paper = self.collectBibData(tmp_paper)
        tmp_paper = self.collectOtherData(tmp_paper)
        return tmp_paper
    
    def collectBibData(self, paper):
        paper.title = self.add_title_input.get()
        paper.year = self.add_year_input.get()

        paper.conference = self.lib.parseConference(self.add_conference.get())
        paper.author = self.lib.parseAuthors(self.add_author_input.get())
        return paper
    
    def collectOtherData(self, paper):
        paper.tag = self.lib.parseTags(self.add_tag_input.get())
        paper.project = self.lib.parseProjects(self.add_project_input.get())
        paper.dataset = self.lib.parseDatasets(self.add_dataset_input.get())

        paper.comment = self.add_comment_input.get(1.0, END)
        paper.path = self.add_path_input.get()

        paper.hasRead = self.hasRead.get()
        paper.hasGithub = self.hasGithub.get()
        return paper
    
    # display data
    
    def displayPaper(self, paper_id, tree_widget):
        tmp_paper = self.lib.papers[paper_id]
        tree_id = tree_widget.insert('', 'end', text=paper_id, values=(tmp_paper.title, tmp_paper.conference, tmp_paper.year))
        return tree_id

    def displayData(self, paper):
        self.displayBibData(paper.bib)
        self.displayOtherData(paper)
    
    def displayBibData(self, bib):
        self.clearBibData()

        self.add_bib_input.insert(1.0, bib)
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

        self.hasRead.set(paper.hasRead)
        self.hasGithub.set(paper.hasGithub)
    
    # clear data
    
    def clearDisplayPapers(self):
        self.display_papers.delete(*self.display_papers.get_children())

    def clearFilter(self):
        self.display_filter.delete(*self.display_filter.get_children())

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