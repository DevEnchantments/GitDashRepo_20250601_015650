# GitDash.py - Complete Version with GitHub Integration and Simple Push Fix

123123import sys
import os
import datetime
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QLineEdit, QTreeWidget, QTreeWidgetItem,
    QListWidget, QTabWidget, QMessageBox, QSplitter, QInputDialog, QStatusBar,
    QAbstractItemView, QToolBar, QFrame, QGroupBox, QDialog, QTextEdit, QCheckBox,
    QMenu, QMenuBar, QProgressBar, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QFont
from git import Repo, GitCommandError
import requests
import urllib.parse

# Try to import PyGithub
try:
    from github import Github, GithubException
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    print("PyGithub not installed. Run: pip install PyGithub")

class GitHubManager:
    def __init__(self, token=None):
        self.token = token
        self.github = Github(token) if token and GITHUB_AVAILABLE else None
        
    def set_token(self, token):
        """Set or update GitHub token"""
        self.token = token
        self.github = Github(token) if GITHUB_AVAILABLE else None
        
    def test_connection(self):
        """Test if token is valid"""
        if not GITHUB_AVAILABLE:
            return False, "PyGithub library not installed"
        try:
            user = self.github.get_user()
            return True, f"Connected as {user.login} ({user.name})"
        except Exception as e:
            return False, str(e)
    
    def create_remote_repo(self, name, description="", private=False):
        """Create a new repository on GitHub"""
        if not GITHUB_AVAILABLE:
            return False, "PyGithub library not installed"
        try:
            user = self.github.get_user()
            repo = user.create_repo(
                name=name,
                description=description,
                private=private,
                auto_init=False  # Don't init, we'll push our local
            )
            return True, repo.clone_url
        except GithubException as e:
            if e.status == 422:
                return False, "Repository name already exists"
            return False, str(e)
        except Exception as e:
            return False, str(e)
    
    def get_user_repos(self):
        """Get list of user's repositories"""
        if not GITHUB_AVAILABLE:
            return []
        try:
            repos = []
            for repo in self.github.get_user().get_repos():
                repos.append({
                    'name': repo.name,
                    'description': repo.description,
                    'url': repo.html_url,
                    'clone_url': repo.clone_url,
                    'private': repo.private
                })
            return repos
        except Exception as e:
            return []

class GitHubSetupDialog(QDialog):
    def __init__(self, parent=None, current_token=None):
        super().__init__(parent)
        self.setWindowTitle("🔐 GitHub Setup")
        self.setModal(True)
        self.resize(500, 400)
        
        self.setStyleSheet(parent.styleSheet() if parent else "")
        
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("🔗 Connect to GitHub")
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Instructions
        instructions = QLabel(
            "To connect to GitHub:\n"
            "1. Go to GitHub.com → Settings → Developer settings\n"
            "2. Click 'Personal access tokens' → 'Tokens (classic)'\n"
            "3. Generate new token with 'repo' scope\n"
            "4. Copy and paste the token below"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("background-color: #2d2d30; padding: 10px; border-radius: 4px;")
        layout.addWidget(instructions)
        
        # Token input
        token_layout = QHBoxLayout()
        token_layout.addWidget(QLabel("Token:"))
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText("ghp_xxxxxxxxxxxxxxxxxxxx")
        if current_token:
            self.token_input.setText(current_token)
        token_layout.addWidget(self.token_input)
        layout.addLayout(token_layout)
        
        # Test connection button
        self.test_btn = QPushButton("🔍 Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        layout.addWidget(self.test_btn)
        
        # Status display
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        self.status_display.setMaximumHeight(100)
        layout.addWidget(self.status_display)
        
        # Save token option
        self.save_token_check = QCheckBox("Save token locally (in .gitdash/config)")
        self.save_token_check.setChecked(True)
        layout.addWidget(self.save_token_check)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setEnabled(False)
        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        self.github_manager = GitHubManager()
        self.is_valid = False
        
    def test_connection(self):
        token = self.token_input.text().strip()
        if not token:
            self.status_display.setText("❌ Please enter a token")
            return
            
        self.status_display.setText("🔄 Testing connection...")
        QApplication.processEvents()
        
        self.github_manager.set_token(token)
        success, message = self.github_manager.test_connection()
        
        if success:
            self.status_display.setText(f"✅ Success! {message}")
            self.save_btn.setEnabled(True)
            self.is_valid = True
        else:
            self.status_display.setText(f"❌ Failed: {message}")
            self.save_btn.setEnabled(False)
            self.is_valid = False
    
    def get_token(self):
        return self.token_input.text().strip() if self.is_valid else None
    
    def should_save_token(self):
        return self.save_token_check.isChecked()

class CreateGitHubRepoDialog(QDialog):
    def __init__(self, parent=None, repo_name=""):
        super().__init__(parent)
        self.setWindowTitle("📦 Create GitHub Repository")
        self.setModal(True)
        self.resize(400, 300)
        
        self.setStyleSheet(parent.styleSheet() if parent else "")
        
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("📦 New GitHub Repository")
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Repository name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Repository Name:"))
        self.name_input = QLineEdit(repo_name)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Description
        desc_layout = QVBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(80)
        self.desc_input.setPlaceholderText("Optional repository description...")
        desc_layout.addWidget(self.desc_input)
        layout.addLayout(desc_layout)
        
        # Private option
        self.private_check = QCheckBox("🔒 Make repository private")
        layout.addWidget(self.private_check)
        
        # Info
        info = QLabel("This will create a repository on GitHub and link it to your local repo.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #7dd3fc; margin: 10px 0;")
        layout.addWidget(info)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.create_btn = QPushButton("✅ Create")
        self.create_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.create_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
    
    def get_repo_info(self):
        return {
            'name': self.name_input.text().strip(),
            'description': self.desc_input.toPlainText().strip(),
            'private': self.private_check.isChecked()
        }

class GitDash(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GitDash - Git GUI Dashboard")
        self.resize(1200, 800)
        self.repo = None
        self.github_manager = GitHubManager()
        self.config_dir = os.path.expanduser("~/.gitdash")
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.load_config()
        
        # Apply modern dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #cccccc;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #cccccc;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            QLineEdit {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #007acc;
                background-color: #2d2d30;
            }
            QPushButton {
                background-color: #0e639c;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                color: white;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #999999;
            }
            QTreeWidget, QListWidget {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                outline: none;
            }
            QTreeWidget::item:selected, QListWidget::item:selected {
                background-color: #094771;
            }
            QTreeWidget::item:hover, QListWidget::item:hover {
                background-color: #2a2d2e;
            }
            QTabWidget::pane {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #2d2d30;
                color: #cccccc;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #252526;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #3e3e42;
            }
            QStatusBar {
                background-color: #007acc;
                color: white;
                font-size: 12px;
            }
            QSplitter::handle {
                background-color: #3e3e42;
                width: 2px;
            }
            QLabel {
                color: #cccccc;
            }
            QGroupBox {
                border: 1px solid #3e3e42;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #cccccc;
            }
            QToolBar {
                background-color: #2d2d30;
                border: none;
                spacing: 3px;
                padding: 4px;
            }
            QToolBar::separator {
                background-color: #3e3e42;
                width: 1px;
                margin: 4px;
            }
            QMenuBar {
                background-color: #2d2d30;
                color: #cccccc;
            }
            QMenuBar::item:selected {
                background-color: #3e3e42;
            }
            QMenu {
                background-color: #252526;
                border: 1px solid #3e3e42;
            }
            QMenu::item:selected {
                background-color: #094771;
            }
        """)

        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Repository section with improved styling
        repo_group = QGroupBox("Repository")
        repo_layout = QHBoxLayout(repo_group)
        
        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText("Select or enter path to your Git repository...")
        repo_layout.addWidget(self.repo_input)

        browse_btn = QPushButton("📁 Browse")
        browse_btn.clicked.connect(self.browse_repo)
        browse_btn.setMaximumWidth(100)
        repo_layout.addWidget(browse_btn)

        open_btn = QPushButton("📂 Open")
        open_btn.clicked.connect(self.open_repo)
        open_btn.setMaximumWidth(100)
        repo_layout.addWidget(open_btn)

        layout.addWidget(repo_group)

        # Main content area
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Left side - Tabs
        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)
        self.tabs.setMinimumWidth(700)

        # Commits Tab
        self.commit_tab = QWidget()
        commit_layout = QVBoxLayout(self.commit_tab)
        commit_layout.setContentsMargins(10, 10, 10, 10)
        
        commit_header = QLabel("📜 Commit History")
        commit_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        commit_layout.addWidget(commit_header)
        
        self.commit_tree = QTreeWidget()
        self.commit_tree.setHeaderLabels(["Hash", "Message", "Author", "Date"])
        self.commit_tree.setRootIsDecorated(False)
        self.commit_tree.setAlternatingRowColors(True)
        commit_layout.addWidget(self.commit_tree)
        self.tabs.addTab(self.commit_tab, "📜 Commits")

        # Branches Tab
        self.branch_tab = QWidget()
        branch_layout = QVBoxLayout(self.branch_tab)
        branch_layout.setContentsMargins(10, 10, 10, 10)
        
        branch_header = QLabel("🌿 Branch Management")
        branch_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        branch_layout.addWidget(branch_header)
        
        self.current_branch_label = QLabel("Current Branch: None")
        self.current_branch_label.setStyleSheet("font-size: 14px; color: #7dd3fc; margin-bottom: 10px;")
        branch_layout.addWidget(self.current_branch_label)
        
        # Remote info
        self.remote_info_label = QLabel("Remote: Not configured")
        self.remote_info_label.setStyleSheet("font-size: 12px; color: #fbbf24; margin-bottom: 10px;")
        branch_layout.addWidget(self.remote_info_label)

        self.branch_list = QListWidget()
        branch_layout.addWidget(self.branch_list)

        branch_btns = QHBoxLayout()
        branch_btns.setSpacing(10)
        
        create_branch_btn = QPushButton("➕ Create Branch")
        create_branch_btn.clicked.connect(self.create_branch)
        branch_btns.addWidget(create_branch_btn)

        delete_branch_btn = QPushButton("🗑️ Delete Branch")
        delete_branch_btn.clicked.connect(self.delete_branch)
        delete_branch_btn.setStyleSheet("""
            QPushButton {
                background-color: #d73a49;
            }
            QPushButton:hover {
                background-color: #cb2431;
            }
        """)
        branch_btns.addWidget(delete_branch_btn)

        checkout_btn = QPushButton("✔️ Checkout")
        checkout_btn.clicked.connect(self.checkout_branch)
        checkout_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ea043;
            }
            QPushButton:hover {
                background-color: #238636;
            }
        """)
        branch_btns.addWidget(checkout_btn)

        branch_layout.addLayout(branch_btns)
        self.tabs.addTab(self.branch_tab, "🌿 Branches")

        # Right side - Staging Area
        self.stage_widget = QWidget()
        self.stage_widget.setMinimumWidth(400)
        stage_layout = QVBoxLayout(self.stage_widget)
        stage_layout.setContentsMargins(10, 10, 10, 10)
        
        stage_header = QLabel("📝 Staging Area")
        stage_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        stage_layout.addWidget(stage_header)

        self.stage_tree = QTreeWidget()
        self.stage_tree.setHeaderLabels(["File", "Status"])
        self.stage_tree.setRootIsDecorated(False)
        self.stage_tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        stage_layout.addWidget(self.stage_tree)

        # Staging buttons with better organization
        stage_btns_frame = QFrame()
        stage_btns_frame.setStyleSheet("background-color: #2d2d30; border-radius: 4px; padding: 10px;")
        stage_btns_layout = QVBoxLayout(stage_btns_frame)
        
        # Row 1: Stage/Unstage
        stage_row1 = QHBoxLayout()
        stage_selected_btn = QPushButton("➕ Stage Selected")
        stage_selected_btn.clicked.connect(self.stage_selected)
        stage_row1.addWidget(stage_selected_btn)

        stage_all_btn = QPushButton("➕ Stage All")
        stage_all_btn.clicked.connect(self.stage_all)
        stage_row1.addWidget(stage_all_btn)

        unstage_btn = QPushButton("➖ Unstage")
        unstage_btn.clicked.connect(self.unstage_selected)
        unstage_btn.setStyleSheet("""
            QPushButton {
                background-color: #6e5494;
            }
            QPushButton:hover {
                background-color: #5a4080;
            }
        """)
        stage_row1.addWidget(unstage_btn)
        stage_btns_layout.addLayout(stage_row1)

        # Row 2: Commit
        commit_btn = QPushButton("✅ Commit Changes")
        commit_btn.clicked.connect(self.commit_changes)
        commit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ea043;
                font-size: 14px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #238636;
            }
        """)
        stage_btns_layout.addWidget(commit_btn)
        
        stage_layout.addWidget(stage_btns_frame)
        splitter.addWidget(self.stage_widget)

        # Set splitter sizes
        splitter.setSizes([700, 400])

        # Status bar with repository info
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Add repository stats to status bar
        self.stats_label = QLabel("")
        self.status_bar.addPermanentWidget(self.stats_label)
        
        # Add GitHub status to status bar
        self.github_status_label = QLabel("GitHub: Not connected")
        self.status_bar.addPermanentWidget(self.github_status_label)

        # Timer for auto-refresh (optional)
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.update_stats)
        self.auto_refresh_timer.start(5000)  # Update every 5 seconds
        
        # Update toolbar based on config
        self.update_github_ui()

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        file_menu.addAction("📂 Open Repository", self.open_repo)
        file_menu.addAction("🆕 Create Repository", self.create_repo)
        file_menu.addSeparator()
        file_menu.addAction("🚪 Exit", self.close)
        
        # GitHub menu
        github_menu = menubar.addMenu("GitHub")
        github_menu.addAction("🔐 Setup GitHub", self.setup_github)
        github_menu.addAction("📦 Create GitHub Repo", self.create_github_repo)
        github_menu.addAction("🔐 Test Push Authentication", self.test_github_push_auth)
        github_menu.addSeparator()
        github_menu.addAction("📋 View My Repos", self.view_github_repos)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("📖 About", self.show_about)

    def create_toolbar(self):
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        
        # Create repo action
        create_action = toolbar.addAction("🆕 New Repo")
        create_action.triggered.connect(self.create_repo)
        
        toolbar.addSeparator()
        
        # Refresh action
        refresh_action = toolbar.addAction("🔄 Refresh")
        refresh_action.triggered.connect(self.refresh_ui)
        
        # Pull action
        self.pull_action = toolbar.addAction("⬇️ Pull")
        self.pull_action.triggered.connect(self.pull_from_github)
        self.pull_action.setEnabled(False)
        
        # Push action
        self.push_action = toolbar.addAction("⬆️ Push")
        self.push_action.triggered.connect(self.push_to_github)
        self.push_action.setEnabled(False)
        
        toolbar.addSeparator()
        
        # GitHub setup
        github_action = toolbar.addAction("🔗 GitHub")
        github_action.triggered.connect(self.setup_github)

    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    if 'github_token' in config:
                        self.github_manager.set_token(config['github_token'])
            except:
                pass
    
    def save_config(self):
        """Save configuration to file"""
        os.makedirs(self.config_dir, exist_ok=True)
        config = {}
        if self.github_manager.token:
            config['github_token'] = self.github_manager.token
        with open(self.config_file, 'w') as f:
            json.dump(config, f)
    
    def update_github_ui(self):
        """Update UI based on GitHub connection status"""
        if self.github_manager.token and GITHUB_AVAILABLE:
            success, message = self.github_manager.test_connection()
            if success:
                self.github_status_label.setText(f"GitHub: ✅ {message.split('(')[1].strip(')')}")
            else:
                self.github_status_label.setText("GitHub: ❌ Invalid token")
        else:
            self.github_status_label.setText("GitHub: Not connected")
        
        # Update push/pull availability
        self.update_remote_actions()
    
    def update_remote_actions(self):
        """Enable/disable push/pull based on remote availability"""
        has_remote = False
        if self.repo:
            try:
                has_remote = 'origin' in self.repo.remotes
                if has_remote:
                    origin = self.repo.remotes.origin
                    self.remote_info_label.setText(f"Remote: {origin.url}")
                else:
                    self.remote_info_label.setText("Remote: Not configured")
            except:
                self.remote_info_label.setText("Remote: Not configured")
        
        self.push_action.setEnabled(has_remote)
        self.pull_action.setEnabled(has_remote)

    def update_stats(self):
        """Update repository statistics in status bar"""
        if self.repo:
            try:
                # Count commits
                commit_count = len(list(self.repo.iter_commits()))
                # Count branches
                branch_count = len(list(self.repo.branches))
                # Count modified files
                modified_count = len(self.repo.index.diff(None))
                
                self.stats_label.setText(f"📊 {commit_count} commits | 🌿 {branch_count} branches | 📝 {modified_count} modified")
            except:
                pass

    # ==== GitHub Integration Methods ====
    
    def setup_github(self):
        """Setup GitHub integration"""
        current_token = self.github_manager.token if self.github_manager else None
        dialog = GitHubSetupDialog(self, current_token)
        if dialog.exec():
            token = dialog.get_token()
            if token:
                self.github_manager = GitHubManager(token)
                
                # Save token if requested
                if dialog.should_save_token():
                    self.save_config()
                
                self.status_bar.showMessage("✅ GitHub connected successfully!")
                self.update_github_ui()
    
    def create_github_repo(self):
        """Create a new GitHub repository and link it"""
        if not self.github_manager.token:
            self.show_error("Please setup GitHub first (GitHub → Setup GitHub)")
            return
        
        if not self.repo:
            self.show_error("Please open a local repository first")
            return
        
        # Check if remote already exists
        if 'origin' in self.repo.remotes:
            self.show_error("This repository already has a remote 'origin' configured.")
            return
        
        # Get repo name from current directory
        repo_name = os.path.basename(self.repo.working_dir)
        
        dialog = CreateGitHubRepoDialog(self, repo_name)
        if dialog.exec():
            info = dialog.get_repo_info()
            
            if not info['name']:
                self.show_error("Repository name cannot be empty")
                return
            
            # Show progress
            self.status_bar.showMessage("Creating GitHub repository...")
            QApplication.processEvents()
            
            # Create remote repository
            success, result = self.github_manager.create_remote_repo(
                info['name'],
                info['description'],
                info['private']
            )
            
            if success:
                # Add remote to local repo
                try:
                    self.repo.create_remote('origin', result)
                    
                    # Push existing commits if any
                    if list(self.repo.iter_commits()):
                        reply = QMessageBox.question(
                            self, 
                            "Push Existing Commits?",
                            "Your local repository has commits. Do you want to push them to GitHub now?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        if reply == QMessageBox.StandardButton.Yes:
                            self.push_to_github()
                    
                    self.show_info(
                        f"✅ GitHub repository created!\n\n"
                        f"Remote URL: {result}\n\n"
                        f"You can now push your commits to GitHub."
                    )
                    self.update_remote_actions()
                except Exception as e:
                    self.show_error(f"Repo created but failed to add remote: {e}")
            else:
                self.show_error(f"Failed to create repository: {result}")
    
    def view_github_repos(self):
        """View list of user's GitHub repositories"""
        if not self.github_manager.token:
            self.show_error("Please setup GitHub first (GitHub → Setup GitHub)")
            return
        
        repos = self.github_manager.get_user_repos()
        if not repos:
            self.show_info("No repositories found or unable to fetch repositories.")
            return
        
        # Create a simple dialog to show repos
        dialog = QDialog(self)
        dialog.setWindowTitle("📋 My GitHub Repositories")
        dialog.setModal(True)
        dialog.resize(600, 400)
        dialog.setStyleSheet(self.styleSheet())
        
        layout = QVBoxLayout(dialog)
        
        header = QLabel(f"📋 Your GitHub Repositories ({len(repos)})")
        header.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)
        
        repo_list = QListWidget()
        for repo in repos:
            item_text = f"📦 {repo['name']}"
            if repo['private']:
                item_text += " 🔒"
            if repo['description']:
                item_text += f"\n   {repo['description']}"
            repo_list.addItem(item_text)
        layout.addWidget(repo_list)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec()
    
    def test_github_push_auth(self):
        """Test if we can authenticate for push operations"""
        if not self.github_manager.token:
            self.show_error("No GitHub token configured")
            return
        
        if not self.repo or 'origin' not in self.repo.remotes:
            self.show_error("Please open a repository with a GitHub remote first")
            return
        
        try:
            # Test token
            g = Github(self.github_manager.token)
            user = g.get_user()
            
            # Get remote info
            origin = self.repo.remotes.origin
            remote_url = origin.url
            
            info = f"✅ Authentication Test Results:\n\n"
            info += f"GitHub User: {user.login}\n"
            info += f"Remote URL: {remote_url}\n"
            info += f"Token: {'✓ Valid' if self.github_manager.token else '✗ Missing'}\n\n"
            
            if remote_url.startswith('https://'):
                info += "Using HTTPS (token authentication)\n"
            elif remote_url.startswith('git@'):
                info += "Using SSH (key authentication)\n"
                info += "⚠️ Note: GitDash uses token auth, consider using HTTPS URLs\n"
            
            self.show_info(info)
            
        except Exception as e:
            self.show_error(f"Authentication test failed:\n{str(e)}")
    
    def push_to_github(self):
        """Push commits to GitHub"""
        if not self.repo:
            self.show_error("No repository open")
            return
        
        try:
            # Check if there are commits to push
            if not list(self.repo.iter_commits()):
                self.show_error("No commits to push. Make some commits first!")
                return
            
            # Check for remote
            if 'origin' not in self.repo.remotes:
                self.show_error("No remote 'origin' configured. Create a GitHub repo first.")
                return
            
            # Get current branch
            try:
                current_branch = self.repo.active_branch.name
            except:
                self.show_error("No active branch found")
                return
            
            # Get remote URL and configure auth
            origin = self.repo.remotes.origin
            original_url = origin.url
            
            self.status_bar.showMessage(f"⬆️ Pushing to GitHub...")
            QApplication.processEvents()
            
            # Configure authentication for HTTPS
            if original_url.startswith('https://') and self.github_manager and self.github_manager.token:
                try:
                    # Get GitHub username
                    g = Github(self.github_manager.token)
                    user = g.get_user()
                    username = user.login
                    
                    # Create authenticated URL
                    parsed = urllib.parse.urlparse(original_url)
                    auth_url = f"https://{username}:{self.github_manager.token}@{parsed.netloc}{parsed.path}"
                    
                    # Set the authenticated URL temporarily
                    with origin.config_writer as cw:
                        cw.set("url", auth_url)
                    
                except Exception as e:
                    self.show_error(f"Failed to configure authentication: {str(e)}")
                    return
            
            try:
                # Disable buttons
                self.push_action.setEnabled(False)
                self.pull_action.setEnabled(False)
                
                # Push with set-upstream
                self.status_bar.showMessage(f"⬆️ Pushing branch '{current_branch}' to origin...")
                QApplication.processEvents()
                
                # Use git command directly
                push_output = self.repo.git.push('--set-upstream', 'origin', current_branch, '--porcelain')
                
                # Restore original URL
                if original_url.startswith('https://'):
                    with origin.config_writer as cw:
                        cw.set("url", original_url)
                
                self.status_bar.showMessage(f"✅ Successfully pushed to origin/{current_branch}")
                self.show_info(f"Push successful!\n\nBranch '{current_branch}' has been pushed to GitHub.")
                self.refresh_ui()
                
            except GitCommandError as e:
                # Restore original URL even on error
                if original_url.startswith('https://'):
                    with origin.config_writer as cw:
                        cw.set("url", original_url)
                
                error_msg = str(e)
                if "authentication failed" in error_msg.lower():
                    self.show_error(
                        "Authentication failed!\n\n"
                        "This usually means:\n"
                        "1. Your GitHub token is invalid or expired\n"
                        "2. The token doesn't have 'repo' permissions\n"
                        "3. The repository doesn't exist on GitHub\n\n"
                        "Please check your GitHub token in GitHub → Setup GitHub"
                    )
                elif "permission denied" in error_msg.lower():
                    self.show_error("Permission denied. Check that your token has 'repo' scope.")
                elif "remote contains work" in error_msg.lower():
                    self.show_error("The remote repository has changes you don't have locally.\nTry pulling first.")
                elif "failed to push" in error_msg.lower():
                    self.show_error(f"Push failed. Make sure:\n1. You have internet connection\n2. The GitHub repo exists\n3. Your token is valid\n\nError: {error_msg}")
                else:
                    self.show_error(f"Push failed:\n{error_msg}")
            finally:
                # Always re-enable buttons
                self.push_action.setEnabled(True)
                self.pull_action.setEnabled(True)
                
        except Exception as e:
            self.show_error(f"Unexpected error during push:\n{str(e)}\n\nType: {type(e).__name__}")
            self.push_action.setEnabled(True)
            self.pull_action.setEnabled(True)
    
    def pull_from_github(self):
        """Pull changes from GitHub"""
        if not self.repo:
            self.show_error("No repository open")
            return
        
        try:
            # Check for remote
            if 'origin' not in self.repo.remotes:
                self.show_error("No remote 'origin' configured")
                return
            
            # Check for uncommitted changes
            if self.repo.is_dirty():
                reply = QMessageBox.question(
                    self,
                    "Uncommitted Changes",
                    "You have uncommitted changes. Pull anyway?\n\n"
                    "This might cause conflicts.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # Get remote URL and configure auth
            origin = self.repo.remotes.origin
            original_url = origin.url
            
            self.status_bar.showMessage("⬇️ Pulling from GitHub...")
            QApplication.processEvents()
            
            # Configure authentication for HTTPS
            if original_url.startswith('https://') and self.github_manager and self.github_manager.token:
                try:
                    # Get GitHub username
                    g = Github(self.github_manager.token)
                    user = g.get_user()
                    username = user.login
                    
                    # Create authenticated URL
                    parsed = urllib.parse.urlparse(original_url)
                    auth_url = f"https://{username}:{self.github_manager.token}@{parsed.netloc}{parsed.path}"
                    
                    # Set the authenticated URL temporarily
                    with origin.config_writer as cw:
                        cw.set("url", auth_url)
                    
                except Exception as e:
                    self.show_error(f"Failed to configure authentication: {str(e)}")
                    return
            
            try:
                # Disable buttons
                self.push_action.setEnabled(False)
                self.pull_action.setEnabled(False)
                
                # Pull
                current_branch = self.repo.active_branch.name
                self.status_bar.showMessage(f"⬇️ Pulling branch '{current_branch}' from origin...")
                QApplication.processEvents()
                
                # Use git command directly
                pull_output = self.repo.git.pull('origin', current_branch)
                
                # Restore original URL
                if original_url.startswith('https://'):
                    with origin.config_writer as cw:
                        cw.set("url", original_url)
                
                self.status_bar.showMessage("✅ Pull completed successfully")
                if "Already up to date" in pull_output:
                    self.show_info("Already up to date!")
                else:
                    self.show_info(f"Pull successful!\n\nChanges pulled from GitHub:\n{pull_output}")
                self.refresh_ui()
                
            except GitCommandError as e:
                # Restore original URL even on error
                if original_url.startswith('https://'):
                    with origin.config_writer as cw:
                        cw.set("url", original_url)
                
                error_msg = str(e)
                if "authentication failed" in error_msg.lower():
                    self.show_error("Authentication failed! Please check your GitHub token.")
                elif "merge conflict" in error_msg.lower():
                    self.show_error("Merge conflict detected! You need to resolve conflicts manually.")
                else:
                    self.show_error(f"Pull failed:\n{error_msg}")
            finally:
                # Always re-enable buttons
                self.push_action.setEnabled(True)
                self.pull_action.setEnabled(True)
                
        except Exception as e:
            self.show_error(f"Unexpected error during pull:\n{str(e)}")
            self.push_action.setEnabled(True)
            self.pull_action.setEnabled(True)
    
    def show_about(self):
        """Show about dialog"""
        about_text = """<h2>GitDash</h2>
        <p>A modern Git GUI Dashboard</p>
        <p>Features:</p>
        <ul>
        <li>Local repository management</li>
        <li>GitHub integration</li>
        <li>Branch management</li>
        <li>Commit history visualization</li>
        </ul>
        <p>Built with PyQt6 and GitPython</p>
        """
        QMessageBox.about(self, "About GitDash", about_text)

    # ==== Core Functionalities ====

    def browse_repo(self):
        path = QFileDialog.getExistingDirectory(self, "Select Git Repository")
        if path:
            self.repo_input.setText(path)

    def open_repo(self):
        path = self.repo_input.text().strip()
        if not path or not os.path.isdir(path):
            self.show_error("Invalid directory path.")
            return
        try:
            self.repo = Repo(path)
            if self.repo.bare:
                self.show_error("The selected directory is not a valid Git repository.")
                self.repo = None
                return
            self.status_bar.showMessage(f"Repository opened: {path}")
            self.refresh_ui()
        except Exception as e:
            self.show_error(f"Failed to open repository:\n{e}")

    def create_repo(self):
        base_dir = QFileDialog.getExistingDirectory(self, "Select Parent Folder for New Git Repository")
        if not base_dir:
            self.status_bar.showMessage("Repository creation canceled.")
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        repo_name = f"GitDashRepo_{timestamp}"
        repo_path = os.path.join(base_dir, repo_name)
        os.makedirs(repo_path, exist_ok=True)

        self.show_info(f"Creating repository at:\n{repo_path}")

        try:
            # Initialize the repository first
            repo = Repo.init(repo_path)
            
            # Create README.md file
            readme_path = os.path.join(repo_path, "README.md")
            with open(readme_path, "w") as f:
                f.write("# New GitDash Repository\nCreated via GitDash GUI.")

            # Add and commit the README to create the first commit
            repo.index.add(['README.md'])
            repo.index.commit("Initial commit - Added README.md")
            
            # Now the repo has a valid HEAD and master branch
            self.repo = repo
            self.repo_input.setText(repo_path)
            self.status_bar.showMessage(f"Initialized new repository at {repo_path}")
            
            # Ask if user wants to create GitHub repo
            if self.github_manager.token:
                reply = QMessageBox.question(
                    self,
                    "Create GitHub Repository?",
                    "Would you like to create a GitHub repository for this project?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.create_github_repo()
            else:
                self.show_info(f"Repository created successfully at:\n{repo_path}\n\nInitial commit with README.md has been created.")
            
            self.refresh_ui()
        except Exception as e:
            self.show_error(f"Failed to initialize repository:\n{e}")

    def refresh_ui(self):
        self.load_commits()
        self.load_branches()
        self.load_stage_changes()
        self.update_stats()
        self.update_remote_actions()

    def load_commits(self):
        self.commit_tree.clear()
        if not self.repo:
            return
        try:
            # Check if repo has any commits
            try:
                commits = list(self.repo.iter_commits(max_count=100))
                for commit in commits:
                    item = QTreeWidgetItem([
                        commit.hexsha[:7],
                        commit.message.strip().split("\n")[0],
                        commit.author.name,
                        commit.committed_datetime.strftime("%Y-%m-%d %H:%M")
                    ])
                    # Color code based on age
                    age_days = (datetime.datetime.now(datetime.timezone.utc) - commit.committed_datetime).days
                    if age_days < 1:
                        item.setForeground(3, Qt.GlobalColor.green)
                    elif age_days < 7:
                        item.setForeground(3, Qt.GlobalColor.yellow)
                    
                    self.commit_tree.addTopLevelItem(item)
            except Exception:
                # No commits yet
                pass
        except Exception as e:
            self.show_error(f"Error loading commits:\n{e}")

    def load_branches(self):
        self.branch_list.clear()
        if not self.repo:
            return
        try:
            try:
                current = self.repo.active_branch.name
                self.current_branch_label.setText(f"Current Branch: 🌿 {current}")
            except TypeError:
                # No branches yet (empty repo)
                self.current_branch_label.setText("Current Branch: (no branches)")
                return

            for branch in self.repo.branches:
                item = self.branch_list.addItem(f"🌿 {branch.name}")
        except Exception as e:
            self.show_error(f"Error loading branches:\n{e}")

    def load_stage_changes(self):
        self.stage_tree.clear()
        if not self.repo:
            return
        try:
            # Get untracked files
            untracked = self.repo.untracked_files
            for file_path in untracked:
                item = QTreeWidgetItem([file_path, "🆕 Untracked"])
                item.setForeground(1, Qt.GlobalColor.red)
                self.stage_tree.addTopLevelItem(item)
            
            # Get modified files (unstaged)
            if self.repo.head.is_valid():
                unstaged = self.repo.index.diff(None)
                for diff in unstaged:
                    item = QTreeWidgetItem([diff.a_path, f"📝 Modified"])
                    item.setForeground(1, Qt.GlobalColor.yellow)
                    self.stage_tree.addTopLevelItem(item)
                
                # Get staged files
                staged = self.repo.index.diff("HEAD")
                for diff in staged:
                    item = QTreeWidgetItem([diff.a_path, f"✅ Staged"])
                    item.setForeground(1, Qt.GlobalColor.green)
                    self.stage_tree.addTopLevelItem(item)
                    
        except Exception as e:
            self.show_error(f"Error loading stage changes:\n{e}")

    def stage_selected(self):
        if not self.repo:
            self.show_error("Open a repository first.")
            return
        selected = self.stage_tree.selectedItems()
        if not selected:
            self.show_error("Select file(s) to stage.")
            return
        try:
            for item in selected:
                self.repo.git.add(item.text(0))
            self.status_bar.showMessage(f"✅ {len(selected)} file(s) staged.")
            self.load_stage_changes()
        except Exception as e:
            self.show_error(f"Error staging files:\n{e}")

    def stage_all(self):
        if not self.repo:
            self.show_error("Open a repository first.")
            return
        try:
            # Check if there are any changes to stage
            if not self.repo.untracked_files and not self.repo.index.diff(None):
                self.status_bar.showMessage("Everything is up to date. Nothing to stage.")
                return
            self.repo.git.add(all=True)
            self.status_bar.showMessage("✅ All changes staged.")
            self.load_stage_changes()
        except Exception as e:
            self.show_error(f"Error staging all files:\n{e}")

    def unstage_selected(self):
        if not self.repo:
            self.show_error("Open a repository first.")
            return
        selected = self.stage_tree.selectedItems()
        if not selected:
            self.show_error("Select file(s) to unstage.")
            return
        try:
            for item in selected:
                self.repo.git.reset(item.text(0))
            self.status_bar.showMessage(f"➖ {len(selected)} file(s) unstaged.")
            self.load_stage_changes()
        except Exception as e:
            self.show_error(f"Error unstaging files:\n{e}")

    def commit_changes(self):
        if not self.repo:
            self.show_error("Open a repository first.")
            return
        commit_msg, ok = QInputDialog.getText(self, "Commit Message", "Enter commit message:")
        if ok and commit_msg.strip():
            try:
                # Check if there are staged changes
                if self.repo.head.is_valid() and not self.repo.index.diff("HEAD"):
                    self.show_error("No staged changes to commit.")
                    return
                elif not self.repo.head.is_valid() and not self.repo.index.entries:
                    self.show_error("No staged changes to commit.")
                    return
                    
                self.repo.index.commit(commit_msg.strip())
                self.status_bar.showMessage("✅ Changes committed successfully!")
                self.load_commits()
                self.load_stage_changes()
            except Exception as e:
                self.show_error(f"Error committing changes:\n{e}")
        else:
            self.status_bar.showMessage("Commit canceled.")

    def create_branch(self):
        if not self.repo:
            self.show_error("Open a repository first.")
            return
        new_branch_name, ok = QInputDialog.getText(self, "Create Branch", "Enter new branch name:")
        if ok and new_branch_name.strip():
            try:
                self.repo.git.branch(new_branch_name.strip())
                self.status_bar.showMessage(f"🌿 Branch '{new_branch_name}' created.")
                self.load_branches()
            except GitCommandError as e:
                self.show_error(f"Error creating branch:\n{e}")

    def delete_branch(self):
        if not self.repo:
            self.show_error("Open a repository first.")
            return
        selected = self.branch_list.currentItem()
        if not selected:
            self.show_error("Select a branch to delete.")
            return
        branch_name = selected.text().replace("🌿 ", "")
        try:
            if branch_name == self.repo.active_branch.name:
                self.show_error("Cannot delete the current active branch.")
                return
        except TypeError:
            pass
        confirm = QMessageBox.question(self, "Confirm Delete", f"Delete branch '{branch_name}'?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.repo.git.branch("-D", branch_name)
                self.status_bar.showMessage(f"🗑️ Branch '{branch_name}' deleted.")
                self.load_branches()
            except GitCommandError as e:
                self.show_error(f"Error deleting branch:\n{e}")

    def checkout_branch(self):
        if not self.repo:
            self.show_error("Open a repository first.")
            return
        selected = self.branch_list.currentItem()
        if not selected:
            self.show_error("Select a branch to checkout.")
            return
        branch_name = selected.text().replace("🌿 ", "")
        try:
            self.repo.git.checkout(branch_name)
            self.status_bar.showMessage(f"✔️ Checked out branch '{branch_name}'.")
            self.load_commits()
            self.load_branches()
            self.load_stage_changes()
        except GitCommandError as e:
            self.show_error(f"Error checking out branch:\n{e}")

    def show_error(self, message):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Error")
        msg.setText(message)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #2d2d30;
                color: #ffffff;
            }
            QMessageBox QPushButton {
                background-color: #0e639c;
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
            }
        """)
        msg.exec()
        self.status_bar.showMessage(f"❌ Error: {message}")

    def show_info(self, message):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Information")
        msg.setText(message)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #2d2d30;
                color: #ffffff;
            }
            QMessageBox QPushButton {
                background-color: #0e639c;
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
            }
        """)
        msg.exec()

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Use Fusion style for better dark theme support
    
    # Check if PyGithub is available
    if not GITHUB_AVAILABLE:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Optional Dependency")
        msg.setText("PyGithub is not installed. GitHub features will be disabled.\n\nTo enable GitHub integration, run:\npip install PyGithub")
        msg.exec()
    
    window = GitDash()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
