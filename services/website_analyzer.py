from urllib.parse import urlparse, urljoin


def analyze_website(html, url):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    title_tag = soup.find("title")
    title = (
        title_tag.get_text(strip=True)
        if title_tag
        else ""
    )

    meta_description_tag = soup.find(
        "meta",
        attrs={"name": "description"}
    )

    meta_description = ""

    if meta_description_tag:
        meta_description = (
            meta_description_tag.get("content", "")
            .strip()
        )

    h1_tags = soup.find_all("h1")
    h2_tags = soup.find_all("h2")

    images = soup.find_all("img")

    images_without_alt = []

    for image in images:
        alt = image.get("alt")

        if alt is None or not alt.strip():
            images_without_alt.append(
                image.get("src", "")
            )

    links = soup.find_all("a")

    empty_links = []

    for link in links:
        text = link.get_text(
            " ",
            strip=True
        )

        aria_label = link.get(
            "aria-label",
            ""
        ).strip()

        title_attribute = link.get(
            "title",
            ""
        ).strip()

        if not text and not aria_label and not title_attribute:
            empty_links.append(
                link.get("href", "")
            )

    page_text = soup.get_text(
        separator=" ",
        strip=True
    )

    word_count = len(
        page_text.split()
    )

    canonical_tag = soup.find(
        "link",
        rel="canonical"
    )

    canonical_url = ""

    if canonical_tag:
        canonical_url = canonical_tag.get(
            "href",
            ""
        ).strip()

        if canonical_url:
            canonical_url = urljoin(
                url,
                canonical_url
            )

    viewport_tag = soup.find(
        "meta",
        attrs={"name": "viewport"}
    )

    parsed_url = urlparse(url)

    is_https = parsed_url.scheme.lower() == "https"

    seo_checks = {
        "title": {
            "passed": bool(title),
            "value": title
        },
        "metaDescription": {
            "passed": bool(meta_description),
            "value": meta_description
        },
        "singleH1": {
            "passed": len(h1_tags) == 1,
            "value": len(h1_tags)
        },
        "canonical": {
            "passed": bool(canonical_url),
            "value": canonical_url
        }
    }

    accessibility_checks = {
        "imageAlt": {
            "passed": len(images_without_alt) == 0,
            "value": len(images_without_alt)
        },
        "linkText": {
            "passed": len(empty_links) == 0,
            "value": len(empty_links)
        }
    }

    technical_checks = {
        "https": {
            "passed": is_https,
            "value": is_https
        },
        "viewport": {
            "passed": viewport_tag is not None,
            "value": (
                viewport_tag.get("content", "")
                if viewport_tag
                else ""
            )
        }
    }

    seo_passed = sum(
        check["passed"]
        for check in seo_checks.values()
    )

    accessibility_passed = sum(
        check["passed"]
        for check in accessibility_checks.values()
    )

    technical_passed = sum(
        check["passed"]
        for check in technical_checks.values()
    )

    seo_score = round(
        (
            seo_passed /
            len(seo_checks)
        ) * 100
    )

    accessibility_score = round(
        (
            accessibility_passed /
            len(accessibility_checks)
        ) * 100
    )

    technical_score = round(
        (
            technical_passed /
            len(technical_checks)
        ) * 100
    )

    overall_score = round(
        (
            seo_score +
            accessibility_score +
            technical_score
        ) / 3
    )

    if overall_score >= 90:
        quality_status = "Excellent"
    elif overall_score >= 75:
        quality_status = "Good"
    elif overall_score >= 50:
        quality_status = "Needs Improvement"
    else:
        quality_status = "Poor"

    return {
        "overallScore": overall_score,
        "qualityStatus": quality_status,
        "seo": {
            "score": seo_score,
            "checks": seo_checks
        },
        "accessibility": {
            "score": accessibility_score,
            "checks": accessibility_checks
        },
        "technical": {
            "score": technical_score,
            "checks": technical_checks
        },
        "content": {
            "wordCount": word_count,
            "h1Count": len(h1_tags),
            "h2Count": len(h2_tags),
            "imageCount": len(images),
            "imagesWithoutAlt": len(
                images_without_alt
            ),
            "linkCount": len(links),
            "emptyLinks": len(
                empty_links
            )
        }
    }