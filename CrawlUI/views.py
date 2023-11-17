import os
import io
import requests
import urllib.request
from django.shortcuts import render, redirect
from Cradose.settings import BASE_DIR
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup

# Create your views here.
def crawl(request):
    return render(request, 'crawl.html')

def done(request):
    # Selected crawled file types
    srcs = request.POST.get('srcs', "0")
    htmls = request.POST.get('htmls', "0")
    pdfs = request.POST.get('pdfs', "0")
    docs = request.POST.get('docs', "0")
    xls = request.POST.get('xls', "0")
    ppts = request.POST.get('ppts', "0")
    imgs = request.POST.get('imgs', "0")
    vids = request.POST.get('vids', "0")
    mp3s = request.POST.get('mp3s', "0")
    zips = request.POST.get('zips', "0")
    
    # Storing the file types in a list
    global filetypes
    filetypes = []
    filetypes.append("srcs" if srcs == "1" else "")
    filetypes.append("htmls" if htmls == "1" else "")
    filetypes.append("pdfs" if pdfs == "1" else "")
    filetypes.append("docs" if docs == "1" else "")
    filetypes.append("xls" if xls == "1" else "")
    filetypes.append("ppts" if ppts == "1" else "")
    filetypes.append("imgs" if imgs == "1" else "")
    filetypes.append("vids" if vids == "1" else "")
    filetypes.append("mp3s" if mp3s == "1" else "")
    filetypes.append("zips" if zips == "1" else "")
    
    # The inputted url
    global parent_url
    parent_url = request.POST['url'] if request.POST['url'].endswith('/') else request.POST['url'] + '/'
    if not parent_url.startswith('https://www.'):
        parent_url = 'https://www.' + parent_url.replace("http://", "").replace("https://", "").replace("www.", "")
    parent_url_file = parent_url[:-1].replace("/", "!").replace(":", ";")
    
    # This will store links we've already checked to prevent duplicates
    global links_list
    links_list = []
    
    # This function counts the number of words in each document
    def count_words():
        print("Counting words in " + parent_url_file)
        
        #This is where we will store the hashmap of documents and there size
        doc_sizes = {}
        
        #Iterating over each file in the directory
        files = [filename for filename in sorted(os.listdir(str(BASE_DIR) + "/Output/Crawled Files/" + parent_url_file)) if not os.path.isdir(str(BASE_DIR) + "/Output/Crawled Files/" + parent_url_file + "/" + filename)]
        for filename in files:
            url = filename.replace("!", "/").replace(";", ":").replace(".txt", "").replace(parent_url,'/')
            doc_sizes[url] = len(open(str(BASE_DIR) + "/Output/Crawled Files/" + parent_url_file + "/" + filename, "r", encoding="utf-8", errors="replace").read().split())
            
        #Create a txt file to store the size of each document for later
        with open(str(BASE_DIR) + "/Output/Document Sizes/" + parent_url_file + ".txt", "w") as output:
            for doc in doc_sizes:
                output.write(doc + ": " + str(doc_sizes[doc]) + "\n" if doc != list(doc_sizes.keys())[-1] else doc + ": " + str(doc_sizes[doc]))
    
    # Creates an inverse index of all the words in the crawled files
    def index():
        print("Indexing " + parent_url_file)
        
        #This is where we will store a hashmap of lists that contain the document number each word appears in and the corresponding frequency
        inverse_indexes = {}

        #Iterating over each file in the directory
        files = [filename for filename in sorted(os.listdir(str(BASE_DIR) + "/Output/Crawled Files/" + parent_url_file)) if not os.path.isdir(str(BASE_DIR) + "/Output/Crawled Files/" + parent_url_file + "/" + filename)]
        for filename in files:
            url = filename.replace("!", "/").replace(";", ":").replace(".txt", "").replace(parent_url,'/')

            #Splitting the text by words and iterating over each word
            file = open(str(BASE_DIR) + "/Output/Crawled Files/" + parent_url_file + "/" + filename, "r", encoding="utf-8", errors="replace").read().split()
            for word in file:

                #If the word is not in the hashmap (first time it appear in any text) we add it to hashmap with a current count of 1
                if word not in inverse_indexes:
                    inverse_indexes[word] = [[url, 1]]

                #If the word is already in the hashmap (even if in a different text)
                else:

                    #If the word is already in the current text just increment the count for this document
                    if inverse_indexes[word][-1][0] == url:
                        inverse_indexes[word][-1][1] += 1

                    #If the word appeared in a previous text but not the current one, add the current document with a count of 1
                    else:
                        inverse_indexes[word].append([url, 1])

        #Create a txt file to store the inverse index for later
        output = open(str(BASE_DIR) + "/Output/Inverted Indexes/" + parent_url_file + ".txt", "w")

        for word in inverse_indexes:
            output.write(word + ": " + str(inverse_indexes[word]) + "\n" if word != list(inverse_indexes.keys())[-1] else word + ": " + str(inverse_indexes[word]))

    # Checks if string has a number in it
    def has_digit(word):
        return any(char.isdigit() for char in word)

    # Checks if string has any punctuation marks in it
    def has_punctuation(word):
        return any(char in ".,?!:;()[]{}*-/" for char in word)

    # Checks if string contains common url formats (Should already be removed by has_punctuation)
    def has_url(word):
        return word.startswith("http://") or word.startswith("https://") or word.startswith("www.")

    # Checks that a string doesn't contain any digits, punctuation, or urls
    def is_valid(word):
        return word.isalpha() and not has_digit(word) and not has_punctuation(word) and not has_url(word)
    
    def remove_junk(url):
        print("Cleaning up " + url)
        
        filename = url.replace("/", "!").replace(":", ";")
        file = open(str(BASE_DIR) + "/Output/Crawled Files/" + parent_url_file + "/" + filename + ".txt", "r+", encoding="utf-8")
        text = file.read()
        
        # Split the text string into a list of words
        words = text.split()
        
        # Remove any words that aren't valid
        valid_words = [word for word in words if is_valid(word)]
        
        # Make all words lowercase
        valid_words = [word.lower() for word in valid_words]
        
        # Keep only the stem words
        for word in valid_words:
            if word.endswith("'s") and word.replace("'s", "") in valid_words:
                valid_words.remove(word)
                valid_words.append(word[:-2])
            elif word.endswith("s") and word.replace("s", "") in valid_words:
                valid_words.remove(word)
                valid_words.append(word[:-1])
                
        file.seek(0)
        file.truncate(0)
        file.write(' '.join(valid_words))
        file.close()
        
    # This function stores the source code of a url
    def store_src(url):
        print("Reading " + url)

        # Since files can't have / in their name, we'll replace them with |
        filename = url.replace("/", "!").replace(":", ";")

        # Pull the text we want to store from the url
        text = requests.get(url).text

        print("Writing " + url)
        # Write the contents of the url to a text file
        os.makedirs(str(BASE_DIR) + "/Output/Crawled Files/" + parent_url_file + "/src/", exist_ok=True)
        file = open(str(BASE_DIR) + "/Output/Crawled Files/" + parent_url_file + "/src/" + filename + ".html", "w", encoding="utf-8")
        file.write(text)
        file.close()
        
    # This function stores the visible text of a url
    def store_html_text(url):
        print("Reading " + url)

        # Since files can't have / in their name, we'll replace them with |
        filename = url.replace("/", "!").replace(":", ";")

        if url.endswith('.pdf') or url.endswith('.pdf/'):
            resource = requests.get(url)
            pdf_file = io.BytesIO(resource.content)
            pdf_text = ""
            try:
                pdf = PdfReader(pdf_file)
                for page in pdf.pages:
                    print(page.extract_text())
                    pdf_text += page.extract_text()
            except:
                print("Error reading PDF file: " + url)
            text = ' '.join(pdf_text.split())
        else:
            text = requests.get(url).text

        # Remove any html tags or extra whitespace from the text
        soup = BeautifulSoup(text, features="lxml")
        text = ' '.join(soup.get_text().split())

        # Split the text string into a list of words
        words = text.split()

        print("Writing " + url)
        # Write the contents of the url to a text file
        os.makedirs(str(BASE_DIR) + "/Output/Crawled Files/" + parent_url_file, exist_ok=True)
        file = open(str(BASE_DIR) + "/Output/Crawled Files/" + parent_url_file + "/" + filename + ".txt", "w", encoding="utf-8")
        for word in words:
            file.write(word + "\n")
        file.close()
        remove_junk(url)
        
    # This function stores the text on a pdf
    def store_pdf(url):
        print("Reading " + url)

        if url.endswith('.pdf/'):
            url = url[:-1]
        
        # Since files can't have / in their name, we'll replace them with |
        filename = url.replace("/", "!").replace(":", ";")
        
        # Pull the text we want to store from the url
        resource = requests.get(url, 
                headers={"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"},
                stream=True,
                verify=False)
        print(resource.status_code)
        

        print("Writing " + url)
        
        # Write the contents of the url to a pdf file
        os.makedirs(str(BASE_DIR) + "/Output/Crawled Files/" + parent_url_file + '/pdfs', exist_ok=True)
        file = open(str(BASE_DIR) + "/Output/Crawled Files/" + parent_url_file + "/pdfs/" + filename + ".pdf", "wb")
        file.write(resource.content)
        file.close()
        
    def store_doc(url):
        print("Reading " + url)

        if url.endswith('.doc/') or url.endswith('.docx/') or url.endswith('.odt/'):
            url = url[:-1]
        
        # Since files can't have / in their name, we'll replace them with |
        filename = url.replace("/", "!").replace(":", ";")
        
        # Pull the text we want to store from the url
        resource = requests.get(url, 
                headers={"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"},
                stream=True,
                verify=False)
        print(resource.status_code)
        

        print("Writing " + url)
        
        # Write the contents of the url to a pdf file
        os.makedirs(str(BASE_DIR) + "/Output/Crawled Files/" + parent_url_file + '/docs', exist_ok=True)
        file = open(str(BASE_DIR) + "/Output/Crawled Files/" + parent_url_file + "/docs/" + filename + ".docx", "wb")
        file.write(resource.content)
        file.close()
        
    def store_xls(url):
        print("Reading " + url)

        if url.endswith('.xls/') or url.endswith('.xlsx/'):
            url = url[:-1]
        
        # Since files can't have / in their name, we'll replace them with |
        filename = url.replace("/", "!").replace(":", ";")
        
        # Pull the text we want to store from the url
        resource = requests.get(url, 
                headers={"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"},
                stream=True,
                verify=False)
        print(resource.status_code)
        

        print("Writing " + url)
        
        # Write the contents of the url to a pdf file
        os.makedirs(str(BASE_DIR) + "/Output/Crawled Files/" + parent_url_file + '/xls', exist_ok=True)
        file = open(str(BASE_DIR) + "/Output/Crawled Files/" + parent_url_file + "/xls/" + filename + ".xlsx", "wb")
        file.write(resource.content)
        file.close()

    # This function checks if a url has other links and calls store_text on them
    def search_links(url, parent_stack):
        print("Searching " + url)
        text = requests.get(url).text

        # Using BeautifulSoup to parse the html for any links that don't have a # in them
        soup = BeautifulSoup(text, features="lxml")
        links = soup.find_all('a')
        
        # Remove any NoneType elements from the links list
        links = [link for link in links if link.get('href') is not None]

        # Remove any links that don't start with the parent url and any links that are just anchors
        links = [link for link in links if "#" not in link.get('href')]
        links = [link for link in links if link.get('href').startswith(parent_url)]

        # If there are no links on the page, just store the text and backtrack
        if not links:
            
            # Make sure we haven't already checked this url
            if url not in links_list:
                links_list.append(url)
                if "srcs" in filetypes:
                    store_src(url)
                if "htmls" in filetypes:
                    store_html_text(url)
                if parent_url.endswith('.pdf') or parent_url.endswith('.pdf/'):
                    if "pdfs" in filetypes:
                        store_pdf(url)
                if parent_url.endswith('.doc') or parent_url.endswith('.docx') or parent_url.endswith('.odt') or parent_url.endswith('.doc/') or parent_url.endswith('.docx/') or parent_url.endswith('.odt/'):
                    if "docs" in filetypes:
                        store_doc(url)
                if parent_url.endswith('.xls') or parent_url.endswith('.xlsx') or parent_url.endswith('.ods') or parent_url.endswith('.xls/') or parent_url.endswith('.xlsx/') or parent_url.endswith('.ods/'):
                    if "xls" in filetypes:
                        store_xls(url)
                
            # If there are more links to check, backtrack to the parent url
            if parent_stack:
                return search_links(parent_stack.pop(), parent_stack)
            
            # If there are no more links to check, we're done
            else:
                return
        
        # Iterate over each link and check its file type
        for link in links:
            try:
                # Make sure the link stays on the parent domain and hasn't already been checked
                if link.get('href') not in links_list and link.get('href') != parent_url:
                    
                    # If the link is a html file, php file, or a directory, we'll store the text and check for more links
                    if link.get('href').endswith('.html') or link.get('href').endswith('.htm') or link.get('href').endswith('.php') or link.get('href').endswith('/') or link.get('href').endswith('htm/') or link.get('href').endswith('html/') or link.get('href').endswith('php/'):
                        links_list.append(link.get('href'))
                        if "srcs" in filetypes:
                            store_src(link.get('href'))
                        if "htmls" in filetypes:
                            store_html_text(link.get('href'))
                        parent_stack.append(url)
                        search_links(link.get('href'), parent_stack)
                    
                    # If the link is a txt file, we'll just store the text
                    elif link.get('href').endswith('.txt') or link.get('href').endswith('.txt/'):
                        links_list.append(link.get('href'))
                        if "srcs" in filetypes:
                            store_src(link.get('href'))
                        if "htmls" in filetypes:
                            store_html_text(link.get('href'))
                        
                    # If the link is a pdf file, we'll just store the text (after preprocessing)
                    elif link.get('href').endswith('.pdf') or link.get('href').endswith('.pdf/'): 
                        links_list.append(link.get('href'))
                        if "src" in filetypes:
                            store_src(link.get('href'))
                        if "htmls" in filetypes:
                            store_html_text(link.get('href'))
                        if "pdfs" in filetypes:
                            store_pdf(link.get('href'))
                            
                    elif link.get('href').endswith('.doc') or link.get('href').endswith('.docx') or link.get('href').endswith('.odt') or link.get('href').endswith('.doc/') or link.get('href').endswith('.docx/') or link.get('href').endswith('.odt/'):
                        links_list.append(link.get('href'))
                        if "srcs" in filetypes:
                            store_src(link.get('href'))
                        if "docs" in filetypes:
                            store_doc(link.get('href'))
                            
                    elif link.get('href').endswith('.xls') or link.get('href').endswith('.xlsx') or link.get('href').endswith('.ods') or link.get('href').endswith('.xls/') or link.get('href').endswith('.xlsx/') or link.get('href').endswith('.ods/'):
                        links_list.append(link.get('href'))
                        if "srcs" in filetypes:
                            store_src(link.get('href'))
                        if "xls" in filetypes:
                            store_xls(link.get('href'))

                    # If the link is a different type (such as an image) we just ignore it
                    else:
                        continue
            except:
                err_file = open(str(BASE_DIR) + "/Output/Errors/" + parent_url_file + ".txt", "a")
                err_file.write("Ignored " + link.get('href') + "\n")
                continue

        # If there are no more links to visit, backtrack to the parent URL
        if parent_stack:
            return search_links(parent_stack.pop(), parent_stack)

    # Search for all links on the page
    search_links(parent_url, [])
    if "htmls" in filetypes:
        index()
        count_words()
    return redirect('search')