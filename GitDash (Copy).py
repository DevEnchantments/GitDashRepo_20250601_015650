import sys
import os
import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QLineEdit, QTreeWidget, QTreeWidgetItem,
    QListWidget, QTabWidget, QMessageBox, QSplitter, QInputDialog, QStatusBar,
    QAbstractItemView
)
from PyQt6.QtCore import Qt
from git import Repo, GitCommandError

class GitDash(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GitDash - Git GUI Dashboard")
        self.resize(1000, 700)
        self.repo = None

        # Central widget and layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Repo selection
        repo_layout = QHBoxLayout()
        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText("Select or enter path to your Git repository...")
        repo_layout.addWidget(self.repo_input)

        browse_btn = QPushButton("Browse")
        browse_btn.setToolTip("Browse for a Git repository folder")
        browse_btn.clicked.connect(self.browse_repo)
        repo_layout.addWidget(browse_btn)

        open_btn = QPushButton("Open Repo")
        open_btn.setToolTip("Open the selected Git repository")
        open_btn.clicked.connect(self.open_repo)
        repo_layout.addWidget(open_btn)

        create_btn = QPushButton("Create Repo")
        create_btn.setToolTip("Create a new Git repository in a selected folder")
        create_btn.clicked.connect(self.create_repo)
        repo_layout.addWidget(create_btn)

        layout.addLayout(repo_layout)

        # Splitter to hold tabs and staging pane
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Tabs for Commits and Branches
        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)
        self.tabs.setMinimumWidth(600)

        # Commit History Tab
        self.commit_tab = QWidget()
        commit_layout = QVBoxLayout(self.commit_tab)
        self.commit_tree = QTreeWidget()
        self.commit_tree.setHeaderLabels(["Hash", "Message", "Author", "Date"])
        self.commit_tree.setAlternatingRowColors(True)
        self.commit_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        commit_layout.addWidget(self.commit_tree)
        self.tabs.addTab(self.commit_tab, "Commits")

        # Branches Tab
        self.branch_tab = QWidget()
        branch_layout = QVBoxLayout(self.branch_tab)

        self.current_branch_label = QLabel("Current Branch: None")
        branch_layout.addWidget(self.current_branch_label)

        self.branch_list = QListWidget()
        branch_layout.addWidget(self.branch_list)

        branch_btn_layout = QHBoxLayout()
        create_branch_btn = QPushButton("Create Branch")
        create_branch_btn.clicked.connect(self.create_branch)
        branch_btn_layout.addWidget(create_branch_btn)

        delete_branch_btn = QPushButton("Delete Branch")
        delete_branch_btn.clicked.connect(self.delete_branch)
        branch_btn_layout.addWidget(delete_branch_btn)

        checkout_branch_btn = QPushButton("Checkout Branch")
        checkout_branch_btn.clicked.connect(self.checkout_branch)
        branch_btn_layout.addWidget(checkout_branch_btn)

        branch_layout.addLayout(branch_btn_layout)
        self.tabs.addTab(self.branch_tab, "Branches")

        # Staging area (right pane)
        self.stage_widget = QWidget()
        stage_layout = QVBoxLayout(self.stage_widget)

        stage_label = QLabel("Stage Changes")
        stage_label.setStyleSheet("font-weight: bold; font-size: 14pt;")
        stage_layout.addWidget(stage_label)

        self.stage_tree = QTreeWidget()
        self.stage_tree.setHeaderLabels(["File", "Status"])
        self.stage_tree.setAlternatingRowColors(True)
        self.stage_tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        stage_layout.addWidget(self.stage_tree)

        stage_btn_layout = QHBoxLayout()
        stage_btn = QPushButton("Stage Selected")
        stage_btn.clicked.connect(self.stage_selected)
        stage_btn_layout.addWidget(stage_btn)

        stage_all_btn = QPushButton("Stage All")
        stage_all_btn.clicked.connect(self.stage_all)
        stage_btn_layout.addWidget(stage_all_btn)

        unstage_btn = QPushButton("Unstage Selected")
        unstage_btn.clicked.connect(self.unstage_selected)
        stage_btn_layout.addWidget(unstage_btn)

        commit_btn = QPushButton("Commit Changes")
        commit_btn.clicked.connect(self.commit_changes)
        stage_btn_layout.addWidget(commit_btn)

        stage_layout.addLayout(stage_btn_layout)

        splitter.addWidget(self.stage_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

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
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Directory to Create Git Repository")
        if not selected_dir:
            self.status_bar.showMessage("Repository creation canceled.")
            return

        try:
            repo = Repo.init(selected_dir)
            self.repo = repo
            self.repo_input.setText(selected_dir)
            self.status_bar.showMessage(f"Initialized new repository at {selected_dir}")
            QMessageBox.information(self, "Repository Created",
                                    f"New repository created at:\n{selected_dir}")
            self.refresh_ui()
        except Exception as e:
            self.show_error(f"Failed to initialize repository:\n{e}")

    def refresh_ui(self):
        self.load_commits()
        self.load_branches()
        self.load_stage_changes()

    def load_commits(self):
        self.commit_tree.clear()
        if not self.repo:
            return
        try:
            if self.repo.head.is_valid():
                for commit in list(self.repo.iter_commits(max_count=100)):
                    item = QTreeWidgetItem([
                        commit.hexsha[:7],
                        commit.message.split("\n")[0],
                        commit.author.name,
                        commit.committed_datetime.strftime("%Y-%m-%d %H:%M")
                    ])
                    self.commit_tree.addTopLevelItem(item)
        except Exception as e:
            self.show_error(f"Error loading commits:\n{e}")

    def load_branches(self):
        self.branch_list.clear()
        if not self.repo:
            return
        try:
            try:
                current = self.repo.active_branch.name
                self.current_branch_label.setText(f"Current Branch: {current}")
            except TypeError:
                self.current_branch_label.setText("Current Branch: (no branches)")

            for branch in self.repo.branches:
                self.branch_list.addItem(branch.name)

            if self.repo.head.is_valid():
                items = self.branch_list.findItems(current, Qt.MatchFlag.MatchExactly)
                if items:
                    self.branch_list.setCurrentItem(items[0])
        except Exception as e:
            self.show_error(f"Error loading branches:\n{e}")

    def load_stage_changes(self):
        self.stage_tree.clear()
        if not self.repo:
            return
        try:
            if not self.repo.head.is_valid():
                return
            unstaged = self.repo.index.diff(None)
            staged = self.repo.index.diff('HEAD')

            def status_str(diff_item):
                if diff_item.change_type == 'M':
                    return "Modified"
                elif diff_item.change_type == 'A':
                    return "Added"
                elif diff_item.change_type == 'D':
                    return "Deleted"
                elif diff_item.change_type == 'R':
                    return "Renamed"
                else:
                    return diff_item.change_type

            for diff in unstaged:
                item = QTreeWidgetItem([diff.a_path, f"Unstaged ({status_str(diff)})"])
                self.stage_tree.addTopLevelItem(item)
            for diff in staged:
                item = QTreeWidgetItem([diff.a_path, f"Staged ({status_str(diff)})"])
                item.setForeground(1, Qt.GlobalColor.darkGreen)
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
                filepath = item.text(0)
                self.repo.git.add(filepath)
            self.status_bar.showMessage("Selected files staged.")
            self.load_stage_changes()
        except Exception as e:
            self.show_error(f"Error staging files:\n{e}")

    def stage_all(self):
        if not self.repo:
            self.show_error("Open a repository first.")
            return
        try:
            unstaged = self.repo.index.diff(None)
            if not unstaged:
                self.status_bar.showMessage("Everything is up to date. Nothing to stage.")
                return
            self.repo.git.add(all=True)
            self.status_bar.showMessage("All changes staged.")
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
                filepath = item.text(0)
                self.repo.git.reset(filepath)
            self.status_bar.showMessage("Selected files unstaged.")
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
                if not self.repo.index.diff("HEAD"):
                    self.show_error("No staged changes to commit.")
                    return
                self.repo.index.commit(commit_msg.strip())
                self.status_bar.showMessage("Changes committed.")
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
                self.status_bar.showMessage(f"Branch '{new_branch_name}' created.")
                self.load_branches()
            except GitCommandError as e:
                self.show_error(f"Error creating branch:\n{e}")
        else:
            self.status_bar.showMessage("Branch creation canceled.")

    def delete_branch(self):
        if not self.repo:
            self.show_error("Open a repository first.")
            return
        selected = self.branch_list.currentItem()
        if not selected:
            self.show_error("Select a branch to delete.")
            return
        branch_name = selected.text()
        try:
            if branch_name == self.repo.active_branch.name:
                self.show_error("Cannot delete the current active branch.")
                return
        except TypeError:
            pass

        confirm = QMessageBox.question(self, "Confirm Delete", f"Delete branch '{branch_name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.repo.git.branch("-D", branch_name)
                self.status_bar.showMessage(f"Branch '{branch_name}' deleted.")
                self.load_branches()
                self.show_error(f"Error deleting branch:\n{e}")
            except GitcommandError as e:
                self.show_error(f"Error deleting branch:\n{e}")

    def checkout_branch(self):
        if not self.repo:
            self.show_error("Open a repository first.")
            return
        selected = self.branch_list.currentItem()
        if not selected:
            self.show_error("Select a branch to checkout.")
            return
        branch_name = selected.text()
        try:
            self.repo.git.checkout(branch_name)
            self.status_bar.showMessage(f"Checked out branch '{branch_name}'.")
            self.load_branches()
            self.load_commits()
            self.load_stage_changes()
        except GitCommandError as e:
            self.show_error(f"Error checking out branch:\n{e}")

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)
        self.status_bar.showMessage("Error: " + message)

def main():
    app = QApplication(sys.argv)
    window = GitDash()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

