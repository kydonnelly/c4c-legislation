from html_table_parser import HTMLTreeNode
from html_table_parser import HTMLTreeParser

def main():
    f = open ('18-1641.html', 'r')
    html_content = f.read()
    f.close()
    
    parser = HTMLTreeParser()
    parser.feed(html_content)
    trees = parser.get_parsed_trees()
    parser.close()

    print('~~~~~~ ALL ~~~~~~')
    [print(tree) for tree in trees]
    print('~~~~~~ TABLE TAGS ~~~~~~')
    [print(table) for table in trees[0].branches_with_tag('table')]
    print('~~~~~~ CMS DATA ~~~~~~')
    [print(cms_table) for cms_table in trees[0].branches_with_data('CMS')]
    print('~~~~~~ TABLES w/ Status ~~~~~~')
    [print(attachment_table) for attachment_table in trees[0].branches_matching('table', 'Status', False)]
    print('~~~~~~ TABLE ROW LEAVES w/ Action Details ~~~~~~')
    [print([leaf for leaf in attachment_table.leaf_data()]) for attachment_table in trees[0].branches_matching('tbody', 'Action details')]

if __name__ == "__main__": 
    main() 
