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

class Category:
    def __init__(self, label):
        self.id = -1
        self.label = label
        self.papers = set()

    # category_str: gui_input, multiple category separated by ';'
    @staticmethod
    def parse(category_str):
        items = category_str.split(';')
        category = []
        for item in items:
            item = item.strip()
            if len(item) < 1 : continue
            category.append(item)
        return category
    
    def addPaper(self, paper):
        if isinstance(paper, Paper) :
            self.papers.add(paper)
    
    def __repr__(self):
        return self.label

class Author(Category):
    def __init__(self, label):
        self.id = -1
        self.label = label
        self.last_name, self.first_name = self.nameParse(label)

        self.papers = set()
    
    @classmethod
    def nameParse(cls, full_name):
        names = full_name.split(',')
        first_name = ""
        last_name = names[0].strip()
        if len(names) > 1 :
            first_name = names[-1].strip()
        return last_name, first_name

    @staticmethod
    def parse(author_str):
        items = author_str.split(' and ')
        authors = []
        for item in items:
            item = item.strip()
            if len(item) < 1 : continue
            authors.append(item)
        return authors

    @staticmethod
    def authorParse(author_str):
        items = Author.parse(author_str)
        authors = []
        for item in items:
            authors.append(Author(item))
        return authors
        

class Project(Category):

    @staticmethod
    def projectParse(project_str):
        items = Category.parse(project_str)
        projects = []
        for item in items:
            projects.append(Project(item))
        return projects

class Tag(Category):

    @staticmethod
    def tagParse(tag_str):
        items = Category.parse(tag_str)
        tags = []
        for item in items:
            tags.append(Tag(item))
        return tags

class Conference(Category):
    def __init__(self, label):
        self.id = -1
        self.label = label
        self.index = 0
        self.alias = None

        self.papers = set()
    
    @staticmethod
    def loadConference(file_name):
        c_map = {}
        with open(file_name) as fin:
            for line in fin.readlines():
                items = line.strip().lower().split('\t')
                if len(items) != 2: continue
                tmp_alias = c_map.get(items[1], set())
                tmp_alias.add(items[0])
                c_map[items[1]] = tmp_alias
        return c_map

DEFAULT_CONFERENCE = Conference("others")

class Dataset(Category):
    
    @staticmethod
    def datasetParse(dataset_str):
        items = Category.parse(dataset_str)
        datasets = []
        for item in items:
            datasets.append(Dataset(item))
        return datasets

first_word_re = re.compile(r'^[a-zA-Z]+')
class Bib:
    
    def __init__(self):
        self._title = ""
        self._author = []
        self._conference = DEFAULT_CONFERENCE
        self._year = DEFAULT_YEAR
        
        self._first_title_word = ""
        self._first_author_name = ""

    @property
    def title(self):
        return self._title
    
    @title.setter
    def title(self, value):
        self._title = value
        m = first_word_re.search(value)
        if m : self._first_title_word = m.group()
    
    @property
    def author(self):
        return " and ".join([a.label for a in self._author])
    
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
        return self._conference.__repr__()
    
    @conference.setter
    def conference(self, value):
        self._conference = DEFAULT_CONFERENCE
        if isinstance(value, Conference) :
            self._conference = value
    
    @property
    def year(self):
        return str(self._year)
    
    @year.setter
    def year(self, value):
        self._year = DEFAULT_YEAR
        if isinstance(value, str) and len(value) > 0:
            value = int(value)
        if isinstance(value, int) and value >= DEFAULT_YEAR and value <= datetime.datetime.now().year : 
            self._year = value
    
    def __repr__(self):
        tmp_cite = self._first_author_name + self.year + self._first_title_word
        return "@inproceedings{{{},\n  title={{{}}},\n  author={{{}}},\n  booktitle={{{}}},\n  year={{{}}}\n}}".format(tmp_cite, self.title, self.author, self.conference, self.year)

title_re = re.compile(r'(?<=[^a-z]title\={).+?(?=})')
author_re = re.compile(r'(?<=[^a-z]author\={).+?(?=})')
conference_re = re.compile(r'(?<=[^a-z]booktitle\={).+?(?=})')
year_re = re.compile(r'(?<=[^a-z]year\={).+?(?=})')
class bibParser:

    @classmethod
    def parse(cls, bib_str, lib):
        b = Bib()
        b.title = cls.titleParser(bib_str)
        b.author = cls.authorParser(bib_str)
        b.conference = cls.conferenceParser(bib_str, lib)
        b.year = cls.yearParser(bib_str)
        return b
    
    @classmethod
    def titleParser(cls, bib_str):
        m = title_re.search(bib_str)
        return m.group() if m else ""
    
    @classmethod
    def authorParser(cls, bib_str):
        m = author_re.search(bib_str)
        return m.group() if m else ""
    
    @classmethod
    def conferenceParser(cls, bib_str, lib):
        m = conference_re.search(bib_str)
        tmp_c = m.group() if m else ""
        return Finder.findConference(tmp_c, lib)
    
    @classmethod
    def yearParser(cls, bib_str):
        m = year_re.search(bib_str)
        return m.group() if m else ""

class Finder:

    @staticmethod
    def findPaper(p, lib):
        if lib is None: return 'hah'
        return None

    @staticmethod
    def findTitle(t_str, lib):
        pass
    
    @staticmethod
    def findAuthor(a_str, lib, support_fuzzy=False):
        for a in lib.authors:
            if a_str.lower() == a.label:
                return a
        return None

    @staticmethod
    def findConference(c_str, lib, support_fuzzy=False):
        for c in lib.conference:
            if c_str.lower() == c.label:
                return c
        return None
    
    @staticmethod
    def findYear(authors):
        pass
    
    @staticmethod
    def findDataset(d_str, lib, support_fuzzy=False):
        for d in lib.datasets:
            if d_str.lower() == d.label:
                return d
        return None
    
    @staticmethod
    def findTag(t_str, lib, support_fuzzy=False):
        for t in lib.tags:
            if t_str.lower() == t.label:
                return t
        return None

    @staticmethod
    def findProject(p_str, lib, support_fuzzy=False):
        for p in lib.projects:
            if p_str.lower() == p.label:
                return p
        return None
    
    @staticmethod
    def findUnread(authors):
        pass
    
    @staticmethod
    def findGithub(authors):
        pass
    
    @staticmethod
    def findCategory(c_str, categories, support_fuzzy=False):
        for c in categories:
            if c_str.lower() == c.label:
                return c
        return None
    
class Paper(object):

    def __init__(self):
        self.id = -1
        # bib information
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
        return self.bib.author
    
    @author.setter
    def author(self, value):
        self.bib.author = value

    @property
    def conference(self):
        return self.bib.conference
    
    @conference.setter
    def conference(self, value):
        self.bib.conference = value
    
    @property
    def year(self):
        return self.bib.year

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
        if os.path.exists(full_path):
            self._path = value

    @property
    def full_path(self):
        return os.path.join(ROOTPATH, self._path)

    @property
    def dataset(self):
        return ";".join([d.label for d in self._dataset])
    
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
        return ";".join([t.label for t in self._tag])
    
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
        return ";".join([p.label for p in self._project])
    
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
        return "title: {}\nauthor: {}\nconference: {}\nyear: {}\npath: {}".format(self.title, self.author, self.conference, self.year, self.full_path)
    
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
        self.papers = set()
        self.conference = set()
        self.years = {}     # {year:set(paper, ...), ...}

        self.authors = set()
        self.datasets = set()
        self.tags = set()
        self.projects = set()

class LibraryGUI:

    def __init__(self):
        self.lib = Library()
        self.cur_paper = Paper()
        self.find_results = []
        self.tree_to_paper = {}     # {tree_id:paper, ...}
        self.paper_to_tree = {}     # {paper:tree_id, ...}
        self.index_to_conference= {}  # {index:conference, ...}

        # gui
        self.root = Tk()
        self.root.title("Cloud Paper Manager")
        self.pages = ttk.Notebook(self.root)
        
        # present
        self.present_page = ttk.Frame(self.pages)

        labelCategory = StringVar()
        labelCategory.set("FilterBy:")
        self.labelCategoryInput = Label(self.present_page, textvariable=labelCategory)
        categories = StringVar()
        self.filter_category = ttk.Combobox(self.present_page, textvariable=categories)

        self.display_filter = ttk.Treeview(self.present_page)  # lists of existing filters

        self.display_category_papers = ttk.Treeview(self.present_page)  # lists of filtered papers

        # add and revise
        self.add_page = ttk.Frame(self.pages)

        self.display_papers = ttk.Treeview(self.add_page)  # lists of existing papers
        self.display_papers['columns'] = ('title', 'conference', 'year')
        # self.display_papers.heading('#0', text='Title')
        self.display_papers['show'] = 'headings'
        self.display_papers.heading('title', text='Title')
        self.display_papers.heading('conference', text='Conference')
        self.display_papers.heading('year', text='Year')
        self.display_papers.bind("<<TreeviewSelect>>", self.selectPaper)
        self.display_papers.bind("<Double-1>", self.openPaper)

        # bibtex parser
        labelBib=StringVar()
        labelBib.set("Bibtex:")
        self.labelBibInput = Label(self.add_page, textvariable=labelBib)
        self.add_bib_input = Text(self.add_page, width=55, height=5)
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

        labelYear = StringVar()
        labelYear.set("Year:")
        self.labelYearInput = Label(self.add_page, textvariable=labelYear)
        self.spinval = StringVar()
        self.add_year_input = Spinbox(self.add_page, from_=1990, to=2020, textvariable=self.spinval)
        
        labelConference = StringVar()
        labelConference.set("Conference:")
        self.labelConferenceInput = Label(self.add_page, textvariable=labelConference)
        conferences = StringVar()
        self.add_conference = ttk.Combobox(self.add_page, textvariable=conferences)

        self.hasRead = BooleanVar()
        self.read_check = ttk.Checkbutton(self.add_page, text='Read', variable=self.hasRead,
	    onvalue=True, offvalue=False)

        labelTag = StringVar()
        labelTag.set("Tags:")
        self.labelTagInput = Label(self.add_page, textvariable=labelTag)
        self.add_tag_input = Entry(self.add_page, width=35)

        labelProject = StringVar()
        labelProject.set("Project:")
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

        self.hasGithub = BooleanVar()
        self.github_check = ttk.Checkbutton(self.add_page, text='Github', variable=self.hasGithub,
	    onvalue=True, offvalue=False)

        self.add_button = Button(self.add_page, command = self.addPaper, text = "Add")
        self.del_button = Button(self.add_page, command = self.delPaper, text = "Remove")
        self.revise_button = Button(self.add_page, command = self.revisePaper, text = "Revise")
        self.find_button = Button(self.add_page, command = self.findPaper, text = "Find")
        self.clear_button = Button(self.add_page, command = self.clear, text = "Reset")
        self.serialize_button = Button(self.add_page, command = self.serialize, text = "Sync")

        # find
        self.find_page = ttk.Frame(self.pages)

        self.ip_input = Entry(self.find_page,width=30)

        # add pages
        self.pages.add(self.present_page, text="Present")
        self.pages.add(self.add_page, text="Add")
        self.pages.add(self.find_page, text="Find")

        # button logic
        # self.bib_parser_button
        # self.add_button
        # self.clear_button
        self.del_button.config(state=DISABLED)     # .config(state=NORMAL)
        # self.find_button
        self.revise_button.config(state=DISABLED) 
        self.serialize_button.config(state=DISABLED)

        # initilization
        # load existing papers
        self.deserialize()
        for p in self.lib.papers:
            tree_id = self.displayPaper(p)
            self.tree_to_paper[tree_id] = p
            self.paper_to_tree[p] = tree_id
        
        self.filter_dict = {'conference':self.lib.conference, 'year':self.lib.years, 'author':self.lib.authors, 'dataset':self.lib.datasets, 'tag':self.lib.tags, 'project':self.lib.projects}
        self.filter_category['value'] = ['please select'] + list(self.filter_dict.keys())
        self.filter_category['state'] = "readonly"
        self.filter_category.current(0)
        self.filter_category.bind('<<ComboboxSelected>>', self.filterListing)

        self.display_filter.heading('#0', text='Filter')
        self.display_filter.bind("<<TreeviewSelect>>", self.filteredPaper)
        
        self.display_category_papers['columns'] = ('title', 'conference', 'year')
        self.display_category_papers['show'] = 'headings'
        self.display_category_papers.heading('title', text='Title')
        self.display_category_papers.heading('conference', text='Conference')
        self.display_category_papers.heading('year', text='Year')
        self.display_category_papers.bind("<Double-1>", self.openCategoryPaper)

        tmp_conference_list = self.initConference(conference_file)
        # generate conference combobox
        self.add_conference['value'] = ['please select'] + tmp_conference_list
        self.add_conference['state'] = "readonly"
        self.add_conference.current(0)
    
    def initConference(self, c_map_file):
        c_map = Conference.loadConference(c_map_file)
        for c in c_map:
            finded_c = Finder.findConference(c, self.lib)
            if finded_c is None:
                tmp_c = Conference(c)
                tmp_c.alias = c_map[c]
                self.lib.conference.add(tmp_c)
            else:
                finded_c.alias |= c_map[c]
        if DEFAULT_CONFERENCE not in self.lib.conference:
            self.lib.conference.add(DEFAULT_CONFERENCE)
        self.index_to_conference[0] = DEFAULT_CONFERENCE
        conference_list = []
        for index, c in enumerate(self.lib.conference):
            conference_list.append(c.label)
            c.index = index + 1
            self.index_to_conference[index + 1] = c
        return conference_list

    # finish gui arrange
    def gui_arrang(self):
        self.pages.grid()
        # present page
        self.labelCategoryInput.grid(row=0, column=0)
        self.filter_category.grid(row=1, column=0)
        self.display_filter.grid(row=2, column=0)
        self.display_category_papers.grid(row=0, column=1, rowspan=3)

        # add page
        self.display_papers.grid(row=0, column=0, rowspan=13)

        self.labelBibInput.grid(row=0, column=1)
        self.bib_parser_button.grid(row=0, column=2)
        self.clear_button.grid(row=0,column=3)
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
        # find page
        self.ip_input.grid()
    
    def serialize(self):
        f = open(lib_file, 'wb')
        pickle.dump(self.lib, f)
        messagebox.showinfo(message='Save lib data success!')
        self.serialize_button.config(state=DISABLED)
    
    def deserialize(self):
        if os.path.exists(lib_file):
            f = open(lib_file, 'rb')
            self.lib = pickle.load(f)

    def filterListing(self, event):
        self.clearFilter()
        filter_name = self.filter_category.get()
        if filter_name in self.filter_dict:
            categories = self.filter_dict[filter_name]
            if filter_name == 'year':
                for c in categories:
                    self.display_filter.insert('', 'end', text=str(c))
            else:
                for c in categories:
                    self.display_filter.insert('', 'end', text=c.label)

    def filteredPaper(self, event):
        tree_id = self.display_filter.focus()
        category_str = self.display_filter.item(tree_id)['text']
        filter_name = self.filter_category.get()
        if filter_name in self.filter_dict:
            categories = self.filter_dict[filter_name]
            if filter_name == 'year':
                pass
            else:
                category = Finder.findCategory(category_str, categories)
                for p in category.papers:
                    self.display_category_papers.insert('', 'end', values=(p.title, p.conference, p.year))
    
    def openCategoryPaper(self):
        pass

    def parseBib(self):
        bib_str = self.add_bib_input.get(1.0,END)
        b = bibParser.parse(bib_str, self.lib)
        self.displayBib(b)
    
    def collectCurBib(self):
        self.cur_paper.title = self.add_title_input.get()
        self.cur_paper.conference = self.index_to_conference[self.add_conference.current()]
        self.cur_paper.author = self.add_author_input.get()
        self.cur_paper.year = self.add_year_input.get()
    
    def collectCurInfo(self):
        self.cur_paper.tag = self.add_tag_input.get()
        self.cur_paper.project = self.add_project_input.get()
        self.cur_paper.dataset = self.add_dataset_input.get()
        self.cur_paper.comment = self.add_comment_input.get(1.0, END)
        self.cur_paper.path = self.add_path_input.get()

        self.cur_paper.hasRead = self.hasRead.get()
        self.cur_paper.hasGithub = self.hasGithub.get()
    
    def addPaper(self):
        # get info for cur paper
        assert self.cur_paper not in self.paper_to_tree, "Paper exist!"

        self.collectCurBib()
        self.collectCurInfo()

        if not self.cur_paper.checkState():
            messagebox.showinfo(message='Please input at least title, author, conference, year and path!')
            return
        p = Finder.findPaper(self.cur_paper, self.lib)
        if p is None:
            tree_id = self.displayPaper(self.cur_paper)
            self.lib.papers.add(self.cur_paper)
            self.cur_paper.bib._conference.addPaper(self.cur_paper)
            y = self.cur_paper.bib._year
            tmp_papers = self.lib.years.get(y, set())
            tmp_papers.add(self.cur_paper)
            self.lib.years[y] = tmp_papers

            for i, a in enumerate(self.cur_paper.bib._author):
                re_a = Finder.findAuthor(a.label, self.lib)
                if re_a is None:
                    a.addPaper(self.cur_paper)
                    self.lib.authors.add(a)
                else:
                    re_a.addPaper(self.cur_paper)
                    self.cur_paper.bib._author[i] = re_a
            
            for i, d in enumerate(self.cur_paper._dataset):
                re_d = Finder.findDataset(d.label, self.lib)
                if re_d is None:
                    d.addPaper(self.cur_paper)
                    self.lib.datasets.add(d)
                else:
                    re_d.addPaper(self.cur_paper)
                    self.cur_paper._dataset[i] = re_d
            
            for i, t in enumerate(self.cur_paper._tag):
                re_t = Finder.findTag(t.label, self.lib)
                if re_t is None:
                    t.addPaper(self.cur_paper)
                    self.lib.tags.add(t)
                else:
                    re_t.addPaper(self.cur_paper)
                    self.cur_paper._tag[i] = re_t
            
            for i, p in enumerate(self.cur_paper._project):
                re_p = Finder.findProject(p.label, self.lib)
                if re_p is None:
                    p.addPaper(self.cur_paper)
                    self.lib.projects.add(p)
                else:
                    re_p.addPaper(self.cur_paper)
                    self.cur_paper._project[i] = re_p

            self.tree_to_paper[tree_id] = self.cur_paper
            self.paper_to_tree[self.cur_paper] = tree_id
            self.clear()

            self.serialize_button.config(state=NORMAL)
        else:
            self.cur_paper = p
            self.displayBib(self.cur_paper._bib)
            self.displayInfo(self.cur_paper)
            self.display_papers.selection_set(self.paper_to_tree[self.cur_paper])

    def selectPaper(self, event):
        tree_id = self.display_papers.focus()
        if len(tree_id) < 1 : return False
        self.cur_paper = self.tree_to_paper[tree_id]
        
        self.displayBib(self.cur_paper.bib)
        self.displayInfo(self.cur_paper)

        # enable buttons to remove or revise self.cur_paper
        self.add_button.config(state=DISABLED)
        self.find_button.config(state=DISABLED)
        self.bib_parser_button.config(state=DISABLED)
        self.del_button.config(state=NORMAL)
        self.revise_button.config(state=NORMAL) 

        return True

    def openPaper(self, event):
        selected = self.selectPaper(event)
        if selected:
            # os.system("open "+tmp_paper.full_path)
            if sys.platform.startswith('darwin'):
                subprocess.call(('open', self.cur_paper.full_path))
            elif os.name == 'nt': # For Windows
                os.startfile(self.cur_paper.full_path)
            elif os.name == 'posix': # For Linux, Mac, etc.
                subprocess.call(('xdg-open', self.cur_paper.full_path))
    
    def revisePaper(self):
        tree_id = self.paper_to_tree[self.cur_paper]

        self.collectCurBib()
        self.collectCurInfo()
        
        self.display_papers.set(tree_id, column='title', value=self.cur_paper.title)
        self.display_papers.set(tree_id, column='conference', value=self.cur_paper.conference)
        self.display_papers.set(tree_id, column='year', value=self.cur_paper.year)

        self.clear()
    
    def findPaper(self):
        pass
    
    def delPaper(self):
        tree_id = self.paper_to_tree[self.cur_paper]
        self.display_papers.delete(tree_id)

        self.lib.papers.remove(self.cur_paper)
        tree_id = self.paper_to_tree[self.cur_paper]
        del self.tree_to_paper[tree_id]
        del self.paper_to_tree[self.cur_paper]

        self.clear()

        self.serialize_button.config(state=NORMAL)
    
    def clear(self):
        self.clearPaperBib()
        self.clearPaperInfo()
        self.cur_paper = Paper()

        self.revise_button.config(state=DISABLED)
        self.del_button.config(state=DISABLED)
        self.find_button.config(state=NORMAL)
        self.add_button.config(state=NORMAL)
        self.bib_parser_button.config(state=NORMAL)
    
    def displayPaper(self, tmp_paper):
        tree_id = self.display_papers.insert('', 'end', values=(tmp_paper.title, tmp_paper.conference, tmp_paper.year))
        return tree_id
    
    def displayBib(self, bib):
        self.clearPaperBib()

        self.add_bib_input.insert(1.0, bib)
        self.add_title_input.insert(0, bib.title)
        self.add_author_input.insert(0, bib.author)
        self.add_conference.current(bib._conference.index)
        self.spinval.set(bib._year)

    def displayInfo(self, paper):
        self.clearPaperInfo()

        self.add_path_input.insert(0, paper.path)
        self.add_tag_input.insert(0, paper.tag)
        self.add_project_input.insert(0, paper.project)
        self.add_dataset_input.insert(0, paper.dataset)
        self.add_comment_input.insert(1.0, paper.comment)

        self.hasRead.set(paper.hasRead)
        self.hasGithub.set(paper.hasGithub)

    def clearFilter(self):
        self.display_filter.delete(*self.display_filter.get_children())

    def clearPaperBib(self):
        self.add_bib_input.delete(1.0, END)
        self.add_title_input.delete(0, 'end')
        self.add_author_input.delete(0, 'end')
        self.add_conference.current(0)
        self.spinval.set(DEFAULT_YEAR)
    
    def clearPaperInfo(self):
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
    lg.gui_arrang()
    # main program
    lg.root.mainloop()
    pass


if __name__ == "__main__":
    main()