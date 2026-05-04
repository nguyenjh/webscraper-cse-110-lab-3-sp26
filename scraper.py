import re
import requests
from urllib.parse import urlparse
from typing import Dict, Optional, List, Set
import time

class StudentRepoValidator:
    """
    Enhanced validator for student GitHub repositories for CSE110 Lab 3
    Checks required files, CSS requirements, AND CSS validation screenshot
    Can validate ANY GitHub repository URL
    """
    
    def __init__(self):
        self.required_files = {
            'README.md': 'README.md file with GitHub Pages URL',
            'standup.md': 'Standup notes template file',
            'css_file': 'CSS stylesheet file (.css)',
            'html_file': 'HTML file (.html)',
            'css_screenshot': 'CSS validation screenshot (.png, .jpg, .jpeg, .gif)'
        }
        
        # Image file extensions for validation screenshot
        self.screenshot_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
        
        # CSS General Topics Requirements
        self.css_general_requirements = {
            'comments': {
                'pattern': r'/\*.*?\*/',
                'description': 'CSS comments (/* comment */)',
                'required': True
            },
            'colors': {
                'pattern': r'color\s*:|background-color\s*:|background\s*:',
                'description': 'Color properties applied',
                'required': True
            },
            'rgb_colors': {
                'pattern': r'rgb\(|rgba\(|#[\da-fA-F]{3,8}|hsl\(|hsla\(|\b(red|green|blue|black|white|orange|purple|yellow|pink|brown)\b',
                'description': 'RGB/RGBA/Hex/HSL/Color names',
                'required': True
            },
            'css_variables': {
                'pattern': r'--[\w-]+:|var\(--[\w-]+\)',
                'description': 'CSS custom properties (variables) with fallback',
                'required': True
            },
            'background': {
                'pattern': r'background(-color|-image|-position|-repeat|-size)?\s*:',
                'description': 'Background styles',
                'required': True
            },
            'units_relative': {
                'pattern': r'\d+(?:em|rem|vh|vw|vmin|vmax|%|ex|ch)',
                'description': 'Relative units (em, rem, vh, vw, %, etc.)',
                'required': True,
                'min_count': 3
            },
            'units_absolute': {
                'pattern': r'\d+(?:px|cm|mm|in|pt|pc)',
                'description': 'Absolute units (px, cm, mm, in, pt, pc)',
                'required': True,
                'min_count': 3
            },
            'box_model_margin': {
                'pattern': r'margin\s*:',
                'description': 'Margin property (should have both long and short)',
                'required': True
            },
            'box_model_padding': {
                'pattern': r'padding\s*:',
                'description': 'Padding property (should have both long and short)',
                'required': True
            },
            'box_model_border': {
                'pattern': r'border(-\w+)?\s*:',
                'description': 'Border properties (style, color, width, radius)',
                'required': True
            },
            'text_styling': {
                'pattern': r'text-(?:decoration|align|transform|indent)|font-\w+|line-height|letter-spacing',
                'description': 'Text styling properties',
                'required': True
            },
            'display_values': {
                'pattern': r'display\s*:\s*(?:none|block|inline-block|inline|flex|grid)',
                'description': 'Display property with various values',
                'required': True,
                'min_unique_values': 2
            },
            'sizing': {
                'pattern': r'(?:width|height|max-width|min-width|max-height|min-height)\s*:',
                'description': 'Sizing properties (width, height, min/max)',
                'required': True
            },
            'positioning': {
                'pattern': r'position\s*:\s*(?:static|relative|fixed|absolute|sticky)',
                'description': 'Position property with various values',
                'required': True,
                'min_unique_values': 2
            },
            'pseudo_classes': {
                'pattern': r':(?:hover|active|focus|visited|link|first-child|last-child|nth-child)',
                'description': 'Pseudo-classes (:hover, :active, etc.)',
                'required': True
            },
            'flexbox': {
                'pattern': r'display\s*:\s*flex|flex-(?:direction|wrap|flow|grow|shrink|basis)|justify-content|align-items|align-content|order',
                'description': 'Flexbox layout properties',
                'required': True,
                'flex_attributes_required': 3
            },
            'grid': {
                'pattern': r'display\s*:\s*grid|grid-template-(?:columns|rows|areas)|grid-(?:column|row|area|gap)|justify-items|align-items',
                'description': 'CSS Grid properties',
                'required': True,
                'grid_attributes_required': 3
            },
            'media_queries': {
                'pattern': r'@media\s+[^{]*\{',
                'description': 'Media queries for responsiveness',
                'required': True
            },
            'third_party_fonts': {
                'pattern': r'@import\s+url\([^)]*fonts\.googleapis\.com|@font-face|font-family:\s*[^;]*?(?:Google\s+Fonts|Poppins|Roboto|Open\s+Sans)',
                'description': 'Third-party fonts (in CSS or HTML)',
                'required': True,
                'check_html_too': True
            }
        }
        
        # CSS Selectors Requirements - ULTRA SIMPLE patterns that just look for the combinator symbols
        self.css_selectors_requirements = {
            'class_selector': {
                'pattern': r'\.[a-zA-Z_][\w-]*(?=[\s\n\r]*[,{])',
                'description': 'Class selector (.classname)',
                'required': True
            },
            'id_selector': {
                'pattern': r'#[a-zA-Z_][\w-]*(?=[\s\n\r]*[,{])',
                'description': 'ID selector (#idname)',
                'required': True
            },
            'universal_selector': {
                'pattern': r'\*(?=[\s\n\r]*[,{])',
                'description': 'Universal selector (*)',
                'required': True
            },
            'element_selector': {
                'pattern': r'^[a-zA-Z][a-zA-Z0-9]*(?=[\s\n\r]*[,{])',
                'description': 'Element selector (div, p, h1, h2, etc.)',
                'required': True
            },
            'attribute_selector': {
                'pattern': r'\[[^\]]+\]',
                'description': 'Attribute selector ([attr=value])',
                'required': True
            },
            'pseudo_class_selector': {
                'pattern': r':[a-zA-Z-]+(?:\([^)]*\))?(?=[\s\n\r]*[,{])',
                'description': 'Pseudo-class selector (:hover, :active, etc.)',
                'required': True
            },
            'selector_list': {
                'pattern': r'[^{},]+\s*,\s*[^{},]+(?=[\s\n\r]*\{)',
                'description': 'Selector list (element, element)',
                'required': True
            },
            'descendant_combinator': {
                'pattern': r'[a-zA-Z0-9#\.][\w-]+\s+[a-zA-Z0-9#\.][\w-]+(?=[\s\n\r]*[,{])',
                'description': 'Descendant combinator (parent child)',
                'required': True
            },
            'child_combinator': {
                'pattern': r'[a-zA-Z0-9#\.][\w-]+\s*>\s*[a-zA-Z0-9#\.][\w-]+',
                'description': 'Child combinator (parent > child)',
                'required': True
            },
            'general_sibling': {
                # Just look for any selector with ~ (anywhere in the CSS)
                'pattern': r'~',
                'description': 'General sibling combinator (element ~ element)',
                'required': True
            },
            'adjacent_sibling': {
                # Just look for any selector with + (anywhere in the CSS)
                'pattern': r'\+',
                'description': 'Adjacent sibling combinator (element + element)',
                'required': True
            },
            'combined_two_selectors': {
                'pattern': r'[a-zA-Z][\w-]*\.[a-zA-Z_][\w-]*(?=[\s\n\r]*[,{])',
                'description': 'Combined selectors (element.class)',
                'required': True
            },
            'has_selector': {
                'pattern': r':has\s*\([^)]+\)',
                'description': ':has() pseudo-class selector (new in 2023)',
                'required': True
            },
            'nested_selectors': {
                'pattern': r'[a-zA-Z0-9#\.][\w-]+\s*\{\s*(?:&)?\s*[a-zA-Z0-9#\.][\w-]+\s*\{',
                'description': 'Nested selectors (new in 2023)',
                'required': True
            }
        }
        
    def validate_repo(self, repo_url: str, check_css_content: bool = True) -> Dict:
        """
        Validate a single GitHub repository (any repository)
        
        Args:
            repo_url: GitHub repository URL
            check_css_content: Whether to check CSS content for requirements
            
        Returns:
            Dictionary with validation results
        """
        # Clean the URL
        repo_url = self._clean_url(repo_url)
        
        # Check if it's a valid GitHub URL
        if not self._is_github_url(repo_url):
            return {
                'url': repo_url,
                'valid': False,
                'error': 'Not a valid GitHub repository URL',
                'details': {}
            }
        
        # Get repository contents via GitHub API
        api_url = self._get_api_url(repo_url)
        if not api_url:
            return {
                'url': repo_url,
                'valid': False,
                'error': 'Could not generate API URL',
                'details': {}
            }
        
        try:
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 404:
                return {
                    'url': repo_url,
                    'valid': False,
                    'error': 'Repository not found or is private',
                    'details': {}
                }
            elif response.status_code == 403:
                return {
                    'url': repo_url,
                    'valid': False,
                    'error': 'Rate limited or repository access denied',
                    'details': {}
                }
            elif response.status_code != 200:
                return {
                    'url': repo_url,
                    'valid': False,
                    'error': f'HTTP {response.status_code}: Could not access repository',
                    'details': {}
                }
            
            contents = response.json()
            files_found = self._check_files(contents)
            
            # Get CSS content if available
            css_content = ""
            css_files_data = []
            if check_css_content and files_found['css_files']:
                for css_file in files_found['css_files_details']:
                    if css_file.get('download_url'):
                        try:
                            css_response = requests.get(css_file['download_url'], timeout=10)
                            if css_response.status_code == 200:
                                css_content += css_response.text + "\n"
                                css_files_data.append({
                                    'name': css_file['name'],
                                    'content': css_response.text
                                })
                        except:
                            pass
            
            # Get HTML content for font checking
            html_content = ""
            html_files_data = []
            if files_found['html_files']:
                for html_file in files_found['html_files_details']:
                    if html_file.get('download_url'):
                        try:
                            html_response = requests.get(html_file['download_url'], timeout=10)
                            if html_response.status_code == 200:
                                html_content += html_response.text + "\n"
                                html_files_data.append({
                                    'name': html_file['name'],
                                    'content': html_response.text
                                })
                        except:
                            pass
            
            # Check CSS requirements (with HTML content for font checking)
            css_general_check = self._check_css_general_requirements(css_content, html_content) if css_content else {}
            css_selectors_check = self._check_css_selectors(css_content) if css_content else {}
            
            # Generate GitHub Pages URL
            pages_url = self._get_pages_url(repo_url)
            
            # Check if Pages site is accessible
            pages_accessible = self._check_pages_accessibility(pages_url)
            
            # Determine overall validity
            files_valid = all([
                files_found['has_readme'],
                files_found['has_standup'],
                files_found['has_css'],
                files_found['has_html'],
                files_found['has_screenshot']
            ])
            
            # Calculate counts for summary
            total_general_required = sum(1 for req in self.css_general_requirements.values() if req.get('required', True))
            total_selectors_required = len(self.css_selectors_requirements)
            
            css_valid = False
            general_missing_count = total_general_required
            selectors_missing_count = total_selectors_required
            missing_general_list = []
            missing_selectors_list = []
            
            if not check_css_content:
                css_valid = True
                general_missing_count = 0
                selectors_missing_count = 0
            elif css_content:
                # Get missing general requirements
                missing_general_list = [req['description'] for req in css_general_check.values() 
                                       if not req.get('found', False) and req.get('required', True)]
                general_missing_count = len(missing_general_list)
                
                # Get missing selectors
                missing_selectors_list = [req['description'] for req in css_selectors_check.values() 
                                         if not req.get('found', False)]
                selectors_missing_count = len(missing_selectors_list)
                
                css_general_all_present = general_missing_count == 0
                css_selectors_all_present = selectors_missing_count == 0
                css_valid = css_general_all_present and css_selectors_all_present
            else:
                css_valid = False
            
            valid = files_valid and css_valid
            
            return {
                'url': repo_url,
                'valid': valid,
                'files_check': files_found,
                'css_general_check': css_general_check,
                'css_selectors_check': css_selectors_check,
                'pages_url': pages_url,
                'pages_accessible': pages_accessible,
                'has_css_content': bool(css_content),
                'has_html_content': bool(html_content),
                'css_files_count': len(files_found['css_files_details']),
                'html_files_count': len(files_found['html_files_details']),
                'summary_counts': {
                    'total_required_files': 5,
                    'files_complete': sum([files_found.get('has_readme', False),
                                          files_found.get('has_standup', False),
                                          files_found.get('has_css', False),
                                          files_found.get('has_html', False),
                                          files_found.get('has_screenshot', False)]),
                    'files_missing_list': self._get_missing_files_list(files_found),
                    'total_general_required': total_general_required,
                    'general_complete': total_general_required - general_missing_count,
                    'general_missing': general_missing_count,
                    'general_missing_list': missing_general_list,
                    'total_selectors_required': total_selectors_required,
                    'selectors_complete': total_selectors_required - selectors_missing_count,
                    'selectors_missing': selectors_missing_count,
                    'selectors_missing_list': missing_selectors_list,
                    'pages_accessible': pages_accessible
                },
                'error': None
            }
            
        except Exception as e:
            return {
                'url': repo_url,
                'valid': False,
                'error': f'Unexpected error: {str(e)}',
                'details': {}
            }
    
    def _get_missing_files_list(self, files_check: Dict) -> List[str]:
        """Get list of missing file names"""
        missing = []
        if not files_check.get('has_readme'):
            missing.append('README.md')
        if not files_check.get('has_standup'):
            missing.append('standup.md')
        if not files_check.get('has_css'):
            missing.append('CSS file (.css)')
        if not files_check.get('has_html'):
            missing.append('HTML file (.html)')
        if not files_check.get('has_screenshot'):
            missing.append('CSS validation screenshot')
        return missing
    
    def _check_css_general_requirements(self, css_content: str, html_content: str = "") -> Dict:
        """Check CSS content for general requirements (including fonts in HTML)"""
        results = {}
        
        for req_name, req_info in self.css_general_requirements.items():
            # Special handling for third-party fonts that can be in HTML
            if req_name == 'third_party_fonts' and req_info.get('check_html_too'):
                css_matches = re.findall(req_info['pattern'], css_content, re.MULTILINE | re.IGNORECASE) if css_content else []
                
                html_font_patterns = [
                    r'<link[^>]*href=["\']https?://fonts\.googleapis\.com[^"\']*["\'][^>]*>',
                    r'@import\s+url\(["\']https?://fonts\.googleapis\.com[^"\']*["\']\)',
                    r'<link[^>]*href=["\'][^"\']*fonts\.googleapis\.com[^"\']*["\'][^>]*>',
                    r'font-family:\s*["\'][^"\']*["\']'
                ]
                
                html_matches = []
                if html_content:
                    for pattern in html_font_patterns:
                        matches = re.findall(pattern, html_content, re.MULTILINE | re.IGNORECASE | re.DOTALL)
                        html_matches.extend(matches)
                
                all_matches = css_matches + html_matches
                found = len(all_matches) > 0
                
                details = {}
                if found:
                    if css_matches:
                        details['location'] = 'CSS file'
                        details['examples'] = css_matches[:2]
                    elif html_matches:
                        details['location'] = 'HTML file'
                        details['examples'] = html_matches[:2]
                
                results[req_name] = {
                    'description': req_info['description'] + ' (in CSS or HTML)',
                    'found': found,
                    'required': req_info['required'],
                    'matches_found': len(all_matches),
                    'details': details
                }
                continue
            
            # Regular pattern matching for other requirements
            matches = re.findall(req_info['pattern'], css_content, re.MULTILINE | re.IGNORECASE | re.DOTALL)
            
            found = len(matches) > 0
            details = {}
            
            # Check for minimum count if specified
            if 'min_count' in req_info:
                unique_matches = set(matches) if matches else set()
                if len(unique_matches) >= req_info['min_count']:
                    found = True
                    details['count'] = len(unique_matches)
                    details['examples'] = list(unique_matches)[:3]
                else:
                    found = False
                    details['count'] = len(unique_matches)
                    details['required'] = req_info['min_count']
            
            # Check for specific flexbox attributes
            if req_name == 'flexbox' and 'flex_attributes_required' in req_info:
                flex_attrs = re.findall(r'(flex-direction|flex-wrap|flex-flow|flex-grow|flex-shrink|flex-basis|justify-content|align-items|align-content|order)', css_content, re.IGNORECASE)
                unique_attrs = set(flex_attrs)
                if len(unique_attrs) >= req_info['flex_attributes_required']:
                    found = True
                    details['flex_attributes_found'] = list(unique_attrs)
                else:
                    found = False
                    details['flex_attributes_needed'] = req_info['flex_attributes_required']
                    details['flex_attributes_found'] = list(unique_attrs)
            
            # Check for specific grid attributes
            if req_name == 'grid' and 'grid_attributes_required' in req_info:
                grid_attrs = re.findall(r'(grid-template-columns|grid-template-rows|grid-template-areas|grid-column|grid-row|grid-area|grid-gap|justify-items|align-items)', css_content, re.IGNORECASE)
                unique_attrs = set(grid_attrs)
                if len(unique_attrs) >= req_info['grid_attributes_required']:
                    found = True
                    details['grid_attributes_found'] = list(unique_attrs)
                else:
                    found = False
                    details['grid_attributes_needed'] = req_info['grid_attributes_required']
                    details['grid_attributes_found'] = list(unique_attrs)
            
            # Check for display value uniqueness
            if req_name == 'display_values' and 'min_unique_values' in req_info:
                display_matches = re.findall(r'display\s*:\s*([^;]+)', css_content, re.IGNORECASE)
                unique_values = set(val.strip() for val in display_matches)
                if len(unique_values) >= req_info['min_unique_values']:
                    found = True
                    details['display_values_found'] = list(unique_values)
                else:
                    found = False
                    details['display_values_needed'] = req_info['min_unique_values']
                    details['display_values_found'] = list(unique_values)
            
            # Check for position value uniqueness
            if req_name == 'positioning' and 'min_unique_values' in req_info:
                position_matches = re.findall(r'position\s*:\s*([^;]+)', css_content, re.IGNORECASE)
                unique_values = set(val.strip() for val in position_matches)
                if len(unique_values) >= req_info['min_unique_values']:
                    found = True
                    details['position_values_found'] = list(unique_values)
                else:
                    found = False
                    details['position_values_needed'] = req_info['min_unique_values']
                    details['position_values_found'] = list(unique_values)
            
            results[req_name] = {
                'description': req_info['description'],
                'found': found,
                'required': req_info['required'],
                'matches_found': len(matches),
                'details': details
            }
        
        return results
    
    def _check_css_selectors(self, css_content: str) -> Dict:
        """Check CSS content for required selectors"""
        results = {}
        
        print(f"\n[DEBUG] Looking for combinators in CSS...")
        
        for selector_name, selector_info in self.css_selectors_requirements.items():
            # Special handling for sibling combinators - just check if the symbol exists
            if selector_name == 'general_sibling':
                # Check if ~ appears in the CSS (and it's not inside a comment or string)
                # Simple approach: just check for ~ with alphanumeric on both sides
                simple_pattern = r'[a-zA-Z0-9_\-.#]+\s*~\s*[a-zA-Z0-9_\-.#]+'
                matches = re.findall(simple_pattern, css_content, re.MULTILINE | re.IGNORECASE)
                found = len(matches) > 0
                if found:
                    print(f"[DEBUG] ✓ Found general sibling combinator (~): {matches[:3]}")
                else:
                    # Check if at least the ~ symbol exists
                    if '~' in css_content:
                        print(f"[DEBUG] ✗ '~' symbol found but not in proper selector format")
            elif selector_name == 'adjacent_sibling':
                # Check if + appears in the CSS (and it's not inside a comment or string)
                simple_pattern = r'[a-zA-Z0-9_\-.#]+\s*\+\s*[a-zA-Z0-9_\-.#]+'
                matches = re.findall(simple_pattern, css_content, re.MULTILINE | re.IGNORECASE)
                found = len(matches) > 0
                if found:
                    print(f"[DEBUG] ✓ Found adjacent sibling combinator (+): {matches[:3]}")
                else:
                    # Check if at least the + symbol exists
                    if '+' in css_content:
                        print(f"[DEBUG] ✗ '+' symbol found but not in proper selector format")
            else:
                matches = list(re.finditer(selector_info['pattern'], css_content, re.MULTILINE | re.DOTALL | re.IGNORECASE))
                found = len(matches) > 0
            
            results[selector_name] = {
                'description': selector_info['description'],
                'found': found,
                'required': selector_info['required'],
                'examples': []
            }
            
            # Add examples for debugging
            if selector_name == 'general_sibling' and found:
                results[selector_name]['examples'] = matches[:2] if 'matches' in locals() else []
            elif selector_name == 'adjacent_sibling' and found:
                results[selector_name]['examples'] = matches[:2] if 'matches' in locals() else []
        
        return results
    
    def _clean_url(self, url: str) -> str:
        """Clean and normalize URL"""
        url = url.strip()
        if url.endswith('/'):
            url = url[:-1]
        if url.endswith('.git'):
            url = url[:-4]
        return url
    
    def _is_github_url(self, url: str) -> bool:
        """Check if URL is a valid GitHub repository URL"""
        patterns = [
            r'github\.com/[^/]+/[^/]+',
            r'raw\.githubusercontent\.com/[^/]+/[^/]+'
        ]
        return any(re.search(pattern, url) for pattern in patterns)
    
    def _get_api_url(self, repo_url: str) -> Optional[str]:
        """Convert GitHub URL to API URL"""
        match = re.search(r'github\.com/([^/]+)/([^/]+)', repo_url)
        if match:
            username = match.group(1)
            repo_name = match.group(2)
            return f"https://api.github.com/repos/{username}/{repo_name}/contents"
        return None
    
    def _get_pages_url(self, repo_url: str) -> str:
        """Generate GitHub Pages URL"""
        match = re.search(r'github\.com/([^/]+)/([^/]+)', repo_url)
        if match:
            username = match.group(1)
            repo_name = match.group(2)
            return f"https://{username}.github.io/{repo_name}"
        return ""
    
    def _check_pages_accessibility(self, pages_url: str) -> bool:
        """Check if GitHub Pages site is accessible"""
        if not pages_url:
            return False
        try:
            response = requests.get(pages_url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _check_files(self, contents: List[Dict]) -> Dict:
        """Check for required files in repository contents"""
        result = {
            'has_readme': False,
            'has_standup': False,
            'has_css': False,
            'has_html': False,
            'has_screenshot': False,
            'readme_content': None,
            'css_files': [],
            'css_files_details': [],
            'html_files': [],
            'html_files_details': [],
            'screenshot_files': [],
            'other_files': []
        }
        
        for item in contents:
            if isinstance(item, dict):
                name = item.get('name', '').lower()
                
                # Check README
                if name == 'readme.md':
                    result['has_readme'] = True
                    if 'download_url' in item:
                        try:
                            readme_response = requests.get(item['download_url'], timeout=5)
                            if readme_response.status_code == 200:
                                result['readme_content'] = readme_response.text[:500]
                        except:
                            pass
                
                # Check standup.md
                elif name == 'standup.md':
                    result['has_standup'] = True
                
                # Check CSS files
                elif name.endswith('.css'):
                    result['has_css'] = True
                    result['css_files'].append(item.get('name'))
                    result['css_files_details'].append({
                        'name': item.get('name'),
                        'download_url': item.get('download_url')
                    })
                
                # Check HTML files
                elif name.endswith('.html'):
                    result['has_html'] = True
                    result['html_files'].append(item.get('name'))
                    result['html_files_details'].append({
                        'name': item.get('name'),
                        'download_url': item.get('download_url')
                    })
                
                # Check for screenshot images
                elif any(name.endswith(ext) for ext in self.screenshot_extensions):
                    screenshot_keywords = ['screenshot', 'validation', 'css-validation', 'validator', 'screen-shot', 'css-check']
                    is_likely_screenshot = any(keyword in name for keyword in screenshot_keywords)
                    
                    if is_likely_screenshot or 'screenshot' in name or 'validation' in name:
                        result['has_screenshot'] = True
                        result['screenshot_files'].append({
                            'name': item.get('name'),
                            'download_url': item.get('download_url'),
                            'size': item.get('size', 0)
                        })
                
                else:
                    result['other_files'].append(item.get('name'))
        
        if not result['has_screenshot']:
            image_files = [item.get('name') for item in contents 
                          if isinstance(item, dict) and 
                          any(item.get('name', '').lower().endswith(ext) for ext in self.screenshot_extensions)]
            if image_files:
                result['possible_screenshots'] = image_files
        
        return result
    
    def print_validation_result(self, result: Dict):
        """Pretty print validation results to terminal"""
        
        print("\n" + "="*80)
        print(f"VALIDATING: {result['url']}")
        print("="*80)
        
        # Check for errors
        if result.get('error'):
            print(f"\n❌ ERROR: {result['error']}")
            return
        
        # Overall status
        if result['valid']:
            print("\n✅ VALID REPOSITORY - All requirements met!")
        else:
            print("\n❌ INCOMPLETE REPOSITORY - Missing requirements")
        
        # File Structure Check
        print("\n" + "="*80)
        print("📁 FILE STRUCTURE CHECK")
        print("="*80)
        
        files_check = result.get('files_check', {})
        
        print("\n📄 Required Files:")
        print("-" * 40)
        
        if files_check.get('has_readme'):
            print("  ✅ README.md - Found")
            if files_check.get('readme_content'):
                pages_pattern = r'https?://[^/]+\.github\.io/[^\s]+'
                if re.search(pages_pattern, files_check['readme_content']):
                    print("     └─ Contains GitHub Pages URL ✓")
                else:
                    print("     └─ ⚠️  Warning: Could not find GitHub Pages URL in README")
        else:
            print("  ❌ README.md - MISSING")
        
        if files_check.get('has_standup'):
            print("  ✅ standup.md - Found")
        else:
            print("  ❌ standup.md - MISSING")
        
        if files_check.get('has_css'):
            css_files = files_check.get('css_files', [])
            print(f"  ✅ CSS File(s) - Found: {', '.join(css_files)}")
        else:
            print("  ❌ CSS File - MISSING (need at least one .css file)")
        
        if files_check.get('has_html'):
            html_files = files_check.get('html_files', [])
            print(f"  ✅ HTML File(s) - Found: {', '.join(html_files)}")
        else:
            print("  ❌ HTML File - MISSING (need at least one .html file)")
        
        print("\n📸 CSS Validation Screenshot:")
        print("-" * 40)
        if files_check.get('has_screenshot'):
            screenshot_files = files_check.get('screenshot_files', [])
            print(f"  ✅ Screenshot found!")
            for screenshot in screenshot_files:
                print(f"     └─ {screenshot['name']} ({screenshot.get('size', 0)} bytes)")
        else:
            print("  ❌ CSS Validation Screenshot - MISSING")
            if files_check.get('possible_screenshots'):
                print(f"     └─ Note: Found image files but none clearly named as screenshot:")
                for img in files_check['possible_screenshots'][:3]:
                    print(f"        - {img}")
                print("     └─ Rename your validation screenshot to include 'screenshot' or 'validation'")
            else:
                print("     └─ No image files found. Please add CSS validation screenshot")
        
        # Get summary counts
        summary = result.get('summary_counts', {})
        
        # QUICK SUMMARY SECTION
        print("\n" + "="*80)
        print("⚡ QUICK SUMMARY - Missing Items Count")
        print("="*80)
        
        files_missing = summary.get('total_required_files', 5) - summary.get('files_complete', 0)
        general_missing = summary.get('general_missing', 0)
        selectors_missing = summary.get('selectors_missing', 0)
        
        print(f"\n  📁 Files Missing:        {files_missing}/5")
        print(f"  🎨 CSS General Missing:   {general_missing}/{summary.get('total_general_required', 0)}")
        print(f"  🔍 CSS Selectors Missing: {selectors_missing}/{summary.get('total_selectors_required', 0)}")
        print(f"  🌐 GitHub Pages:          {'✅ Working' if summary.get('pages_accessible') else '❌ Not accessible'}")
        
        if files_missing > 0 or general_missing > 0 or selectors_missing > 0:
            print(f"\n  📊 TOTAL MISSING: {files_missing + general_missing + selectors_missing} items")
        
        # FINAL SUMMARY with detailed missing items
        print("\n" + "="*80)
        print("📊 FINAL SUMMARY - Detailed Missing Items")
        print("="*80)
        
        # Missing Files
        missing_files_list = summary.get('files_missing_list', [])
        if missing_files_list:
            print(f"\n  Missing {len(missing_files_list)} required files:")
            for file in missing_files_list:
                print(f"     - {file}")
        else:
            print("\n  ✅ All required files present!")
        
        # Missing CSS General Topics
        missing_general_list = summary.get('general_missing_list', [])
        if missing_general_list:
            print(f"\n  Missing {len(missing_general_list)} CSS general topics:")
            for item in missing_general_list:
                print(f"     - {item}")
        else:
            if result.get('has_css_content'):
                print("\n  ✅ All CSS general topics present!")
            else:
                print("\n  ⚠️  No CSS content found to validate")
        
        # Missing CSS Selectors
        missing_selectors_list = summary.get('selectors_missing_list', [])
        if missing_selectors_list:
            print(f"\n  Missing {len(missing_selectors_list)} CSS selectors:")
            for selector in missing_selectors_list:
                print(f"     - {selector}")
        else:
            if result.get('has_css_content'):
                print("\n  ✅ All CSS selectors present!")
            else:
                print("\n  ⚠️  No CSS content found to validate selectors")
        
        # GitHub Pages Status
        print(f"\n  🌐 GitHub Pages: {'✅ Accessible' if summary.get('pages_accessible') else '❌ Not accessible'}")
        if not summary.get('pages_accessible') and result.get('pages_url'):
            print(f"     URL: {result.get('pages_url')}")
            print(f"     Action: Enable GitHub Pages in repository settings")
        
        # Overall Progress
        total_complete = (summary.get('files_complete', 0) + 
                         summary.get('general_complete', 0) + 
                         summary.get('selectors_complete', 0))
        total_required = (summary.get('total_required_files', 5) + 
                         summary.get('total_general_required', 0) + 
                         summary.get('total_selectors_required', 0))
        
        print(f"\n  📈 OVERALL PROGRESS: {total_complete}/{total_required} ({int((total_complete/total_required)*100)}%)")
        
        if not result['valid']:
            print("\n  🔧 PRIORITY FIXES NEEDED:")
            priority_count = 1
            if not files_check.get('has_readme'):
                print(f"     {priority_count}. Add README.md with GitHub Pages URL")
                priority_count += 1
            if not files_check.get('has_standup'):
                print(f"     {priority_count}. Add standup.md with standup meeting template")
                priority_count += 1
            if not files_check.get('has_css'):
                print(f"     {priority_count}. Add CSS file")
                priority_count += 1
            if not files_check.get('has_html'):
                print(f"     {priority_count}. Add HTML file")
                priority_count += 1
            if not files_check.get('has_screenshot'):
                print(f"     {priority_count}. Add CSS validation screenshot")
                priority_count += 1
            if not summary.get('pages_accessible'):
                print(f"     {priority_count}. Enable GitHub Pages in repository settings")
                priority_count += 1
            if missing_general_list:
                print(f"     {priority_count}. Add {len(missing_general_list)} missing CSS general topics (see list above)")
                priority_count += 1
            if missing_selectors_list:
                print(f"     {priority_count}. Add {len(missing_selectors_list)} missing CSS selectors (see list above)")
                priority_count += 1
        
        print("\n" + "="*80 + "\n")


class InteractiveValidator:
    """
    Interactive terminal validator that accepts links one by one
    Can validate ANY GitHub repository URL
    """
    
    def __init__(self):
        self.validator = StudentRepoValidator()
        self.checked_repos = []
        
    def run(self):
        """Run the interactive validator"""
        self.print_header()
        
        while True:
            print("\n" + "─"*80)
            url = input("\n📝 Enter any GitHub repository URL (or 'quit' to exit): ").strip()
            
            if url.lower() in ['quit', 'exit', 'q', 'done']:
                self.print_summary()
                break
            
            if not url:
                print("⚠️  Please enter a valid URL")
                continue
            
            print("\n🔍 Validating repository... (this may take a few seconds)")
            
            result = self.validator.validate_repo(url)
            self.checked_repos.append(result)
            self.validator.print_validation_result(result)
    
    def print_header(self):
        """Print the welcome header"""
        print("\n" + "="*80)
        print("🎓 GitHub Repository Validator - CSE110 Lab 3 Requirements")
        print("="*80)
        print("\n📋 This validator checks for CSE110 Lab 3 requirements:")
        print("\n  Required Files (5 items):")
        print("    - README.md (with GitHub Pages URL)")
        print("    - standup.md (standup notes template)")
        print("    - .css file (stylesheet)")
        print("    - .html file (meeting minutes)")
        print("    - CSS validation screenshot")
        print("\n  CSS General Topics (20 items):")
        print("    - Comments, Colors, CSS Variables, Background, Units")
        print("    - Box Model (margin, padding, border)")
        print("    - Text styling, Display, Sizing, Positioning")
        print("    - Pseudo-classes, Flexbox, Grid")
        print("    - Media Queries, 3rd Party Fonts (in CSS or HTML)")
        print("\n  CSS Selectors (14 items):")
        print("    - Class, ID, Universal, Element, Attribute")
        print("    - Pseudo-class, Selector List")
        print("    - All 4 Combinator types")
        print("    - Combined selectors, :has(), Nested selectors")
        print("\n💡 You can validate ANY GitHub repository URL")
        print("   The tool will check for all lab requirements regardless of repository name")
    
    def print_summary(self):
        """Print summary of all checked repositories"""
        if not self.checked_repos:
            print("\nNo repositories were checked. Goodbye!")
            return
        
        print("\n" + "="*80)
        print("📊 SESSION SUMMARY - All Checked Repositories")
        print("="*80)
        
        total = len(self.checked_repos)
        valid = sum(1 for r in self.checked_repos if r.get('valid', False))
        invalid = total - valid
        
        print(f"\nTotal repositories checked: {total}")
        print(f"✅ Valid (complete): {valid}")
        print(f"❌ Invalid (incomplete): {invalid}")
        
        if invalid > 0:
            print("\n\n❌ INCOMPLETE REPOSITORIES WITH DETAILS:")
            print("-" * 80)
            for idx, repo in enumerate(self.checked_repos, 1):
                if not repo.get('valid', False) and not repo.get('error'):
                    summary = repo.get('summary_counts', {})
                    files_missing_count = len(summary.get('files_missing_list', []))
                    general_missing_count = summary.get('general_missing', 0)
                    selectors_missing_count = summary.get('selectors_missing', 0)
                    
                    print(f"\n{idx}. {repo['url']}")
                    print(f"   📁 Missing: {files_missing_count} files  |  🎨 Missing: {general_missing_count} general  |  🔍 Missing: {selectors_missing_count} selectors")
                    
                    # Show specific missing items for first few incomplete repos
                    if idx <= 3:
                        missing_files = summary.get('files_missing_list', [])
                        if missing_files:
                            print(f"   Missing files: {', '.join(missing_files)}")
                        
                        missing_general = summary.get('general_missing_list', [])
                        if missing_general and len(missing_general) <= 5:
                            print(f"   Missing general: {', '.join(missing_general)}")
                        elif missing_general:
                            print(f"   Missing general: {len(missing_general)} items")
                        
                        missing_selectors = summary.get('selectors_missing_list', [])
                        if missing_selectors and len(missing_selectors) <= 5:
                            print(f"   Missing selectors: {', '.join(missing_selectors)}")
                        elif missing_selectors:
                            print(f"   Missing selectors: {len(missing_selectors)} items")
        
        if valid > 0:
            print("\n\n✅ COMPLETE REPOSITORIES:")
            print("-" * 80)
            for idx, repo in enumerate(self.checked_repos, 1):
                if repo.get('valid', False):
                    print(f"\n{idx}. {repo['url']}")
                    if repo.get('pages_accessible'):
                        print(f"   🌐 Pages: {repo['pages_url']}")
        
        print("\n" + "="*80)
        print("Goodbye! 👋")
        print("="*80 + "\n")


def quick_check():
    """Quick function to check a single repository from command line"""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python scraper.py <github-repo-url>")
        print("Example: python scraper.py https://github.com/username/repository-name")
        return
    
    validator = StudentRepoValidator()
    url = sys.argv[1]
    print(f"\n🔍 Validating {url}...\n")
    result = validator.validate_repo(url)
    validator.print_validation_result(result)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        quick_check()
    else:
        interactive = InteractiveValidator()
        try:
            interactive.run()
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted by user. Goodbye!")
            if interactive.checked_repos:
                interactive.print_summary()