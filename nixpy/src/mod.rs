use regex::Regex;


// From the packaging python module
const VERSION_PATTERN: &str = r"
v?
(?:
    (?:(?P<epoch>[0-9]+)!)?                           # epoch
    (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
    (?P<pre>                                          # pre-release
        [-_\.]?
        (?P<pre_l>alpha|a|beta|b|preview|pre|c|rc)
        [-_\.]?
        (?P<pre_n>[0-9]+)?
    )?
    (?P<post>                                         # post release
        (?:-(?P<post_n1>[0-9]+))
        |
        (?:
            [-_\.]?
            (?P<post_l>post|rev|r)
            [-_\.]?
            (?P<post_n2>[0-9]+)?
        )
    )?
    (?P<dev>                                          # dev release
        [-_\.]?
        (?P<dev_l>dev)
        [-_\.]?
        (?P<dev_n>[0-9]+)?
    )?
)
(?:\+(?P<local>[a-z0-9]+(?:[-_\.][a-z0-9]+)*))?       # local version
";

enum LocalPart {
    Identifier(String),
    Number(u32),
}

struct VersionError {
    message: String
}

struct Version {
    epoch: u32,
    release: Vec<u32>,
    dev: Option<(String, u32)>,
    pre: Option<(String, u32)>,
    post: Option<(String, u32)>,
    local: Option<Vec<LocalPart>>
}

impl Version {
    fn parse(version: &str) -> Result<Version, VersionError> {
        let re = Regex::new(VERSION_PATTERN).unwrap();
    }
}

struct Project {
    name: String,
    version: String,
}

#[cfg(test)]
mod test {
    #[test]
    fn test_version() {
        let version = Version::parse("1.2.3").unwrap();
    }
}