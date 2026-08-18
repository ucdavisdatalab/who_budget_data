# World Health Organization Budget Dataset

[top]: #world-health-organization-budget-data

_Authors: Joey Suen, Nick Ulle, Lauren Peritz_  
_Maintainer: Nick Ulle <<naulle@ucdavis.edu>>_  

This repository contains code to post-process data extracted from World Health
Organization (WHO) Budget PDFs. The repository also contains code for some
initial exploratory analysis of the dataset. 

> [!IMPORTANT]
>
> This repository only contains the code and documentation for the dataset. It
> does not include the dataset itself (nor the `data/` directory).
>
> The dataset is provided separately.

The purpose of this project is to make historical data about voluntary
contributions to the WHO more easily accessible. The project was proposed by
Lauren Peritz and carried out by the [UC Davis DataLab][datalab].

[datalab]: https://datalab.ucdavis.edu/


## File and Directory Structure

The directory structure for the project is:

```
data/               Datasets
figures/            Graphics and figures
notebooks/          Notebooks (`.ipynb`, `.Rmd`, ...)
src/                Python/Java/... (non-R) source code
R/                  R source code
.gitattributes      Paths Git should give special treatment
.gitignore          Paths Git should ignore
CONTRIBUTING.md     Instructions for contributing to this project
LICENSE             License for the code
LICENSE-DATA        License for the dataset
README.md           This file
README-DATA.md      Documentation for the dataset
pixi.lock           Exact description of Pixi environment (dependencies)
pixi.toml           Project metadata file (including dependencies)
```

<!--
The files in the `data/` directory are:

```

```
-->

([back to top][top])


## Installation

To get started, open a terminal (Git Bash on Windows) and clone a copy of this
repo:

```
git clone git@github.com:datalab-dev/2025_law_youtube.git
```

Then follow the instructions in the next section to set up the necessary
software environment.


### Pixi

We use [Pixi][], a fast package manager based on the conda ecosystem, to
install the packages required to build this reader. To install Pixi, follow
[the official instructions][Pixi]. 

[pixi]: https://pixi.sh/

The `pixi.toml` file in this repo lists required packages, while the
`pixi.lock` file lists package versions for each platform. When the lock file
is present, Pixi will attempt to install the exact versions listed. Deleting
the lock file allows Pixi to install other versions, which might help if
installation fails (but beware of inconsistencies between package versions).

To install the required packages, open a terminal and navigate to this repo's
directory. Then run:

```sh
pixi install
```

This will automatically create a virtual environment and install the packages.

To open a shell in the virtual environment, run:

```sh
pixi shell
```

You can run the `pixi shell` command from the repo directory or any of its
subdirectories. Use the virtual environment to run any commands related to
building the reader. When you're finished using the virtual environment, you
can use the `exit` command to exit the shell.

([back to top][top])
