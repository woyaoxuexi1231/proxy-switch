use crate::models::ProxyConfig;

const PROXY_ID: &str = "proxy-switch-http";
const MIRROR_ID: &str = "proxy-switch-mirror";

pub fn has_proxy_url(config: &ProxyConfig) -> bool {
    !config.http_proxy.is_empty() || !config.https_proxy.is_empty()
}

pub fn parse_host_port(url: &str) -> (String, String) {
    if url.is_empty() {
        return (String::new(), String::new());
    }
    let stripped = url
        .trim_start_matches("http://")
        .trim_start_matches("https://")
        .trim_start_matches("socks5://");
    if let Some(pos) = stripped.rfind(':') {
        let host = &stripped[..pos];
        let port = stripped[pos + 1..].split('/').next().unwrap_or("");
        (host.to_string(), port.to_string())
    } else {
        (stripped.to_string(), String::new())
    }
}

pub fn find_proxy(xml: &str) -> (bool, Option<String>) {
    if xml.trim().is_empty() {
        return (false, None);
    }
    if !xml.contains(PROXY_ID) {
        return (false, None);
    }
    let re_active = regex::Regex::new(r"<active>\s*true\s*</active>").unwrap();
    if !re_active.is_match(xml) {
        return (false, None);
    }
    let re_host = regex::Regex::new(r"<host>\s*([^<\s]+)\s*</host>").unwrap();
    let re_port = regex::Regex::new(r"<port>\s*(\d+)\s*</port>").unwrap();
    let re_proto = regex::Regex::new(r"<protocol>\s*([^<\s]+)\s*</protocol>").unwrap();
    if let (Some(h), Some(p)) = (re_host.captures(xml), re_port.captures(xml)) {
        let protocol = re_proto
            .captures(xml)
            .map(|c| c[1].to_string())
            .unwrap_or_else(|| "http".into());
        (true, Some(format!("{}://{}:{}", protocol, &h[1], &p[1])))
    } else {
        (false, None)
    }
}

pub fn find_mirror(xml: &str) -> Option<String> {
    if xml.trim().is_empty() || !xml.contains(MIRROR_ID) {
        return None;
    }
    // Prefer the url that belongs to our mirror block.
    let re = regex::Regex::new(
        r"(?s)<mirror>\s*<id>\s*proxy-switch-mirror\s*</id>.*?<url>\s*([^<\s]+)\s*</url>",
    )
    .unwrap();
    if let Some(cap) = re.captures(xml) {
        return Some(cap[1].to_string());
    }
    let re_url = regex::Regex::new(r"<url>\s*([^<\s]+)\s*</url>").unwrap();
    re_url.captures(xml).map(|c| c[1].to_string())
}

/// Apply proxy and/or mirror. Empty proxy URL leaves existing proxy alone;
/// empty mirror URL leaves existing mirror alone.
pub fn apply(existing: &str, config: &ProxyConfig) -> Result<String, String> {
    let want_proxy = has_proxy_url(config);
    let want_mirror = !config.mirror.is_empty();
    if !want_proxy && !want_mirror {
        return Err("Proxy URL or Maven mirror URL is required".into());
    }

    let mut xml = if existing.trim().is_empty() {
        empty_settings()
    } else {
        existing.to_string()
    };

    if want_proxy {
        let url = if !config.https_proxy.is_empty() {
            &config.https_proxy
        } else {
            &config.http_proxy
        };
        let (host, port) = parse_host_port(url);
        let mut non_proxy = config.no_proxy.replace(',', "|");
        non_proxy.retain(|c| !c.is_whitespace());
        if non_proxy.is_empty() {
            non_proxy = "localhost|127.0.0.1".into();
        }
        xml = upsert_proxy(&xml, &host, &port, &non_proxy);
    }

    if want_mirror {
        xml = upsert_mirror(&xml, &config.mirror);
    }

    Ok(xml)
}

pub fn remove_proxy(xml: &str) -> String {
    regex::Regex::new(r"(?s)\s*<proxy>\s*<id>\s*proxy-switch-http\s*</id>.*?</proxy>")
        .unwrap()
        .replace_all(xml, "")
        .to_string()
}

fn empty_settings() -> String {
    r#"<?xml version="1.0" encoding="UTF-8"?>
<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.0.0
                              http://maven.apache.org/xsd/settings-1.0.0.xsd">
</settings>
"#
    .to_string()
}

fn proxy_block(host: &str, port: &str, non_proxy: &str) -> String {
    let host = if host.is_empty() { "127.0.0.1" } else { host };
    let port = if port.is_empty() { "8080" } else { port };
    format!(
        r#"    <proxy>
      <id>{PROXY_ID}</id>
      <active>true</active>
      <protocol>http</protocol>
      <host>{host}</host>
      <port>{port}</port>
      <nonProxyHosts>{non_proxy}</nonProxyHosts>
    </proxy>
"#
    )
}

fn mirror_block(url: &str) -> String {
    format!(
        r#"    <mirror>
      <id>{MIRROR_ID}</id>
      <name>Aliyun Maven</name>
      <url>{url}</url>
      <mirrorOf>*</mirrorOf>
    </mirror>
"#
    )
}

fn upsert_proxy(xml: &str, host: &str, port: &str, non_proxy: &str) -> String {
    let xml = remove_proxy(xml);
    let block = proxy_block(host, port, non_proxy);
    if xml.contains("<proxies>") {
        let re = regex::Regex::new(r"(?s)(<proxies>\s*)").unwrap();
        return re.replace(&xml, format!("${{1}}{block}")).to_string();
    }
    insert_before_settings_end(&xml, &format!("  <proxies>\n{block}  </proxies>\n"))
}

fn remove_our_mirror(xml: &str) -> String {
    regex::Regex::new(r"(?s)\s*<mirror>\s*<id>\s*proxy-switch-mirror\s*</id>.*?</mirror>")
        .unwrap()
        .replace_all(xml, "")
        .to_string()
}

fn upsert_mirror(xml: &str, url: &str) -> String {
    let xml = remove_our_mirror(xml);
    let block = mirror_block(url);
    if xml.contains("<mirrors>") {
        let re = regex::Regex::new(r"(?s)(<mirrors>\s*)").unwrap();
        return re.replace(&xml, format!("${{1}}{block}")).to_string();
    }
    insert_before_settings_end(&xml, &format!("  <mirrors>\n{block}  </mirrors>\n"))
}

fn insert_before_settings_end(xml: &str, block: &str) -> String {
    let re = regex::Regex::new(r"(?s)(</settings>)").unwrap();
    re.replace(xml, format!("{block}</settings>")).to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cfg(http: &str, mirror: &str) -> ProxyConfig {
        ProxyConfig {
            http_proxy: http.into(),
            https_proxy: String::new(),
            no_proxy: String::new(),
            mirror: mirror.into(),
        }
    }

    #[test]
    fn mirror_only_writes_mirrors_not_proxy() {
        let xml = apply("", &cfg("", "https://maven.aliyun.com/repository/public")).unwrap();
        assert!(xml.contains("<mirrors>"));
        assert!(xml.contains("maven.aliyun.com"));
        assert!(xml.contains("<mirrorOf>*</mirrorOf>"));
        assert!(!xml.contains("<proxies>"));
    }

    #[test]
    fn proxy_then_aliyun_keeps_proxy() {
        let with_proxy = apply("", &cfg("http://127.0.0.1:7890", "")).unwrap();
        let with_both = apply(
            &with_proxy,
            &cfg("", "https://maven.aliyun.com/repository/public"),
        )
        .unwrap();
        assert!(with_both.contains("127.0.0.1"));
        assert!(with_both.contains("maven.aliyun.com"));
        let (enabled, _) = find_proxy(&with_both);
        assert!(enabled);
        assert_eq!(
            find_mirror(&with_both).as_deref(),
            Some("https://maven.aliyun.com/repository/public")
        );
    }

    #[test]
    fn disable_proxy_keeps_aliyun_mirror() {
        let xml = apply(
            "",
            &cfg(
                "http://127.0.0.1:7890",
                "https://maven.aliyun.com/repository/public",
            ),
        )
        .unwrap();
        let xml = remove_proxy(&xml);
        assert!(!xml.contains(PROXY_ID));
        assert!(xml.contains("maven.aliyun.com"));
    }
}
