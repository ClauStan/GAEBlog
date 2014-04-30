from __future__ import division

import os
import urllib
import webapp2
import jinja2
import re
import logging
import math
import cgi
import datetime

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import memcache

JINJA_ENVIRONMENT = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)), extensions=['jinja2.ext.autoescape'])

class Post(db.Model):
        url = db.StringProperty()
	title = db.StringProperty()
	content = db.TextProperty()
	summary = db.TextProperty()
	author = db.StringProperty()
	author_slug = db.StringProperty()
	date_created = db.DateTimeProperty(auto_now_add=True)
	date_modified = db.DateTimeProperty()
	tags = db.StringListProperty()
	
class Tag(db.Model):
	name = db.StringProperty()
	occurrences = db.IntegerProperty()
	date_created = db.DateTimeProperty(auto_now_add=True)

class Author(db.Model):
        name = db.StringProperty()
        name_slug = db.StringProperty()

class Comment(db.Model):	
	post = db.ReferenceProperty(Post, collection_name='comments')
	content = db.TextProperty()
	author = db.StringProperty()
	date_created = db.DateTimeProperty(auto_now_add=True)

class Utility():
        postsPerPage = 4
        title = "Blog Title"
        subtitle = "blog subtitle"
        about = "Brief text about your blog"
        otherLinks = {"My 1st cool link":"https://google.com/" , "My 2st cool link":"https://appspot.com"}

        @staticmethod
        def Slugify(inStr):
                removelist = ["a", "an", "as", "at", "before", "but", "by", "for", "from", "is", "in", "into", "like", "of", "off", "on", "onto", "per", "since", "than", "the", "this", "that", "to", "up", "via", "with"];
                for a in removelist:
                        aslug = re.sub(r'\b'+a+r'\b','',inStr)
                aslug = re.sub('[^\w\s-]', '', aslug).strip().lower()
                aslug = re.sub('\s+', '-', aslug)
                return aslug

        @staticmethod
        def UserIsAdmin():
                user = users.get_current_user()
                if user and users.is_current_user_admin():
                        return True
                return False
                        
        @staticmethod
        def ConstructFontSizes():
                minOccur = 9999
                maxOccur = -1
                fontMin = 10
                fontMax = 50
                fontSizes = {}
                
                tagQuery = Tag.gql("ORDER BY date_created DESC")
                tagList = tagQuery.fetch(limit=15)
                for tag in tagList:
                        if tag.occurrences > maxOccur:
                                maxOccur = tag.occurrences
                        if tag.occurrences < minOccur:
                                minOccur = tag.occurrences
                                
                for tag in tagList:
                        size = fontMin
                        
                        if tag.occurrences > minOccur:
                                size = int(math.ceil(fontMin + (fontMax-fontMin)*((tag.occurrences-minOccur)/(maxOccur-minOccur))))
                                
                        fontSizes[tag.name] = size
                                
                return fontSizes               
                        
	@staticmethod
	def GetFontSizes():
                fontSizes = memcache.get('fontSizes')
                if fontSizes is not None:
                        return fontSizes
                else:
                        fontSizes = Utility.ConstructFontSizes()
                        memcache.add('fontSizes', fontSizes, 60)
                        return fontSizes

        @staticmethod
	def SetStaticBlogValues(template):
                template['title'] = Utility.title
                template['subtitle'] = Utility.subtitle
                template['about'] = Utility.about
                template['otherLinks'] = Utility.otherLinks
                

class HomePage(webapp2.RequestHandler):
        def get(self):
                postAll = Post.all()
                postAll.order("-date_created")
                postList = postAll.fetch(limit=Utility.postsPerPage)

                template_values = {'postList' : postList}

                count = Post.all(keys_only=True).count()
                if(count>Utility.postsPerPage):
                        template_values['rightButton'] = '1'

                tagCloud = Utility.GetFontSizes()
                template_values['tagCloud'] = tagCloud
                
                if Utility.UserIsAdmin():
                        template_values['isAdmin'] = True

                Utility.SetStaticBlogValues(template_values)
                
                template = JINJA_ENVIRONMENT.get_template('home.html')
                self.response.write(template.render(template_values))
        
class NamePage(webapp2.RequestHandler):
        def get(self, page_nr):
                pageNr = int(page_nr)
                count = Post.all(keys_only=True).count()
                if (pageNr == 0 or (pageNr*Utility.postsPerPage+1 <= count)):
                        postAll = Post.all()
                        postAll.order("-date_created")
                        postList = postAll.fetch(offset=pageNr*Utility.postsPerPage, limit=Utility.postsPerPage)

                        template_values = {'postList' : postList}
                        
                        if(pageNr>0):
                                template_values['leftButton'] = str(pageNr-1)
                        if((pageNr+1)*Utility.postsPerPage < count):
                                template_values['rightButton'] = str(pageNr+1)

                        tagCloud = Utility.GetFontSizes()
                        template_values['tagCloud'] = tagCloud

                        if Utility.UserIsAdmin():
                                template_values['isAdmin'] = True

                        Utility.SetStaticBlogValues(template_values)
                        
                        template = JINJA_ENVIRONMENT.get_template('home.html')
                        self.response.write(template.render(template_values))       
                else:
                        self.response.write("This page doesnt exist silly! ")

class SearchByTagPage(webapp2.RequestHandler): 
        def get(self, tag, page_nr):
                pageNr = int(page_nr)
                count = Post.gql("WHERE tags = :1", tag).count()
                if ((pageNr == 0 and count > 0) or (pageNr*Utility.postsPerPage+1 <= count)):
                        postWithTags = Post.gql("WHERE tags = :1 ORDER by date_created DESC", tag)
                        postList = postWithTags.fetch(offset=pageNr*Utility.postsPerPage, limit=Utility.postsPerPage)
                        
                        template_values = {'postList' : postList}
                        template_values['tag'] = tag
                        
                        if(pageNr>0):
                                template_values['leftButton'] = str(pageNr-1)
                        if((pageNr+1)*Utility.postsPerPage < count):
                                template_values['rightButton'] = str(pageNr+1)

                        tagCloud = Utility.GetFontSizes()
                        template_values['tagCloud'] = tagCloud
                
                        if Utility.UserIsAdmin():
                                template_values['isAdmin'] = True

                        Utility.SetStaticBlogValues(template_values)
                        
                        template = JINJA_ENVIRONMENT.get_template('searchbytag.html')
                        self.response.write(template.render(template_values))
                else:
                        self.response.write("This page doesnt exist silly! ")

class SearchByAuthorPage(webapp2.RequestHandler): 
        def get(self, author_slug, page_nr):
                pageNr = int(page_nr)
                count = Post.gql("WHERE author_slug = :1", author_slug).count()
                if ((pageNr == 0 and count > 0) or (pageNr*Utility.postsPerPage+1 <= count)):
                        postByAuthor = Post.gql("WHERE author_slug = :1 ORDER by date_created DESC", author_slug)
                        postList = postByAuthor.fetch(offset=pageNr*Utility.postsPerPage, limit=Utility.postsPerPage)
                        
                        template_values = {'postList' : postList}
                        template_values['author_slug'] = author_slug

                        authorQuery = Author.gql("WHERE name_slug = :1", author_slug)
                        authorList = authorQuery.fetch(limit=1)
                        author = authorList[0].name
                        
                        template_values['author'] = author
                     
                        if(pageNr>0):
                                template_values['leftButton'] = str(pageNr-1)
                        if((pageNr+1)*Utility.postsPerPage < count):
                                template_values['rightButton'] = str(pageNr+1)

                        tagCloud = Utility.GetFontSizes()
                        template_values['tagCloud'] = tagCloud

                        if Utility.UserIsAdmin():
                                template_values['isAdmin'] = True

                        Utility.SetStaticBlogValues(template_values)
                        
                        template = JINJA_ENVIRONMENT.get_template('searchbyauthor.html')
                        self.response.write(template.render(template_values))
                else:
                        self.response.write("This page doesnt exist silly! ")
                                                
		
class AboutPage(webapp2.RequestHandler):
        def get(self):
                template = JINJA_ENVIRONMENT.get_template('about.html')

                template_values = {}

                tagCloud = Utility.GetFontSizes()
                template_values['tagCloud'] = tagCloud

                if Utility.UserIsAdmin():
                        template_values['isAdmin'] = True

                Utility.SetStaticBlogValues(template_values)
                
                self.response.write(template.render(template_values))

class AdminPage(webapp2.RequestHandler):
        def get(self):
                postAll = Post.all()
                postAll.order("-date_created")
                postList = postAll.fetch(limit=500)

                template_values = {'postList' : postList}

                tagCloud = Utility.GetFontSizes()
                template_values['tagCloud'] = tagCloud

                if Utility.UserIsAdmin():
                        template_values['isAdmin'] = True

                Utility.SetStaticBlogValues(template_values)
                
                template = JINJA_ENVIRONMENT.get_template('admin.html')
                self.response.write(template.render(template_values)) 
		
class CreatePostPage(webapp2.RequestHandler):
        def get(self):
		template = JINJA_ENVIRONMENT.get_template('create_post.html')

                template_values = {}

                tagCloud = Utility.GetFontSizes()
                template_values['tagCloud'] = tagCloud
                
                if Utility.UserIsAdmin():
                        template_values['isAdmin'] = True

                Utility.SetStaticBlogValues(template_values)
                
                self.response.write(template.render(template_values))
	def post(self):
                newPost = Post()
                title  = self.request.get('Title')
                newPost.title = title
                newPost.url = Utility.Slugify(inStr=title)
                newPost.summary = self.request.get('Summary')
                newPost.content = self.request.get('Content')
                tagList = self.request.get('Tags').split(',')
                newPost.tags = tagList      
                authorName = self.request.get('Author')
                newPost.author = authorName
                authorSlug = Utility.Slugify(inStr=authorName)
                newPost.author_slug = authorSlug
                newPost.put()

                for tag in tagList:
                        if Tag.gql("WHERE name = :1", tag).count() == 0 :
                                newTag = Tag()
                                newTag.name = tag
                                newTag.occurrences = 1
                                newTag.put()
                        else:
                                foundTag = Tag.gql("WHERE name = :1", tag).fetch(limit=1)
                                foundTag[0].occurrences += 1
                                foundTag[0].put()

                if Author.gql("WHERE name = :1", authorName).count() == 0 :
                        newAuthor = Author()
                        newAuthor.name = authorName                
                        newAuthor.name_slug = authorSlug     
                        newAuthor.put()
         
                self.redirect("/admin")
		
class EditPostPage(webapp2.RequestHandler):
	def get(self, post_url):
                postList = Post.gql("WHERE url = :1", post_url)
                post = None
                for p in postList.run(limit=1):
                        post = p

                if post == None:
                        self.response.write("There is no such post silly")
                else:
                        template_values = {'post' : post}

                        tagCloud = Utility.GetFontSizes()
                        template_values['tagCloud'] = tagCloud

                        if Utility.UserIsAdmin():
                                template_values['isAdmin'] = True

                        Utility.SetStaticBlogValues(template_values)
                        
                        template = JINJA_ENVIRONMENT.get_template('edit_post.html')
                        self.response.write(template.render(template_values))
        
	def post(self, post_url):
                postList = Post.gql("WHERE url = :1", post_url)
                post = None
                for p in postList.run(limit=1):
                        post = p

                if post == None:
                        self.response.write("There is no such post silly "+post_url)
                else:
                        title  = self.request.get('Title')
                        post.title = title
                        post.url = Utility.Slugify(inStr=title)
                        post.summary = self.request.get('Summary')
                        post.content = self.request.get('Content')
                        oldTagList = post.tags
                        newTagList = self.request.get('Tags').split(',')
                        post.tags = newTagList
                        authorName = self.request.get('Author')
                        post.author = authorName
                        authorSlug = Utility.Slugify(inStr=authorName)
                        post.author_slug = authorSlug
                        post.date_modified = datetime.datetime.now()
                        post.put()

                        incrTagList = newTagList    
                        decrTagList = oldTagList

                        for tag in oldTagList:
                                if newTagList.count(tag) == 1:
                                        incrTagList.remove(tag)
                                        decrTagList.remove(tag)

                        for tag in incrTagList:
                                if Tag.gql("WHERE name = :1", tag).count() == 0 :
                                        newTag = Tag()
                                        newTag.name = tag
                                        newTag.occurrences = 1
                                        newTag.put()
                                else:
                                        foundTag = Tag.gql("WHERE name = :1", tag).fetch(limit=1)
                                        foundTag[0].occurrences += 1
                                        foundTag[0].put()

                        for tag in decrTagList:
                                if Tag.gql("WHERE name = :1", tag).count() > 0 :
                                        foundTag = Tag.gql("WHERE name = :1", tag).fetch(limit=1)

                                        if foundTag[0].occurrences == 1:
                                                foundTag[0].delete()
                                        else:
                                                foundTag[0].occurrences -= 1
                                                foundTag[0].put()

                        if Author.gql("WHERE name = :1", authorName).count() == 0 :
                                newAuthor = Author()
                                newAuthor.name = authorName                
                                newAuthor.name_slug = authorSlug     
                                newAuthor.put()
                        
                        self.redirect("/admin")

class DeletePostPage(webapp2.RequestHandler):
	def post(self):
		self.response.write("Post cannot be deleted for now...");
		
class ShowPostPage(webapp2.RequestHandler):
	def get(self, post_url):
                postQuery = Post.gql("WHERE url = :1", post_url)
                foundPost = None
                for post in postQuery.run(limit=1):
                        foundPost = post

                if foundPost == None:
                        self.response.write("There is not such post silly!") 
                else:        
                        template_values = {'foundPost' : foundPost}

                        commentQuery = Comment.gql("WHERE post = :1 ORDER BY date_created DESC", foundPost.key())
                        commentList = commentQuery.run()

                        template_values['commentList'] = commentList

                        tagCloud = Utility.GetFontSizes()
                        template_values['tagCloud'] = tagCloud
                        
                        if Utility.UserIsAdmin():
                                template_values['isAdmin'] = True

                        Utility.SetStaticBlogValues(template_values)
                        
                        template = JINJA_ENVIRONMENT.get_template('showpost.html')
                        self.response.write(template.render(template_values))

class AddCommentPage(webapp2.RequestHandler):
	def post(self, post_url):
                postList = Post.gql("WHERE url = :1", post_url)
                post = None
                for p in postList.run(limit=1):
                        post = p

                newComment = Comment()
                newComment.post = post
                newComment.content = self.request.get('Comment')
                newComment.author = self.request.get('Author')
                newComment.put()

                self.redirect("/post/"+post_url)
                

app = webapp2.WSGIApplication([
	('/', HomePage),
        ('/page/(\d*)', NamePage),
	('/about', AboutPage),
	('/post/([\da-z-]+)', ShowPostPage),
        ('/addcomment/([\da-z-]+)', AddCommentPage),
        ('/searchbytag/([\da-z-]+)/page/(\d*)', SearchByTagPage),
        ('/searchbyauthor/([\da-z-]+)/page/(\d*)', SearchByAuthorPage),
        ('/admin', AdminPage),
	('/admin/createpost', CreatePostPage),
	('/admin/editpost/([\da-z-]+)', EditPostPage),
        ('/admin/deletepost/([\da-z-]+)', DeletePostPage)
], debug=True)
