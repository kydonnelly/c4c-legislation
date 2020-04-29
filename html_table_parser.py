from html.parser import HTMLParser

class HTMLTreeNode:
	def __init__(self, parent, tag, attrs):
		self.tag = tag
		self.attrs = attrs
		self.parent = parent
		self.data = None
		self.children = []

	def branches_with_tag(self, target):
		matches = []
		if self.tag == target:
			matches.append(self)
		for child in self.children:
			matches += child.branches_with_tag(target)
		return matches

	def branches_with_data(self, data):
		matches = []
		if self.matches_data(data):
			matches.append(self)
		for child in self.children:
			matches += child.branches_with_data(data)
		return matches

	def branches_matching(self, tag, data, allow_nesting = False):
		matches = []
		for child in self.children:
			matches += child.branches_matching(tag, data, allow_nesting)

		if len(matches) == 0 or allow_nesting:
			if self.tag == tag and self.branch_has_data(data):
				matches.append(self)

		return matches

	def branch_has_data(self, target):
		if self.matches_data(target):
			return True

		for child in self.children:
			if child.branch_has_data(target):
				return True

		return False

	def matches_data(self, target):
		return self.data != None and target in self.data

	def leaf_data(self):
		data = []
		if len(self.children) == 0:
			if self.data != None:
				data.append(self.data)
		else:
			for child in self.children:
				data = data + child.leaf_data()

		return data

	def __str__(self):
		return self.print(0)

	def print(self, indent_level):
		components = []
		components.append("  " * indent_level)
		components.append(self.tag)
		components.append(', '.join(["{0}: {1}".format(k, v) for k, v in self.attrs.items()]))
		if self.data != None:
			components.append(self.data)

		print_str = ' '.join(components) + "\n"
		for child in self.children:
			print_str += child.print(indent_level + 1)
		return print_str

class HTMLTreeParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.roots = []
        self.current_node = None

    def handle_starttag(self, tag, attrs):
        attributes = { k: v for (k, v) in attrs }
        if self.current_node == None:
        	self.current_node = HTMLTreeNode(None, tag, attributes)
        	self.roots.append(self.current_node)
        else:
        	parent = self.current_node
        	self.current_node = HTMLTreeNode(parent, tag, attributes)
        	parent.children.append(self.current_node)

    def handle_endtag(self, tag):
        if self.current_node != None:
        	self.current_node = self.current_node.parent

    def handle_data(self, data):
    	# ignore whitespace and newlines
    	stripped = data.rstrip().replace(u'\xa0', ' ')
    	if self.current_node != None and stripped != None:
    		self.current_node.data = stripped

    def get_parsed_trees(self):
    	return self.roots
