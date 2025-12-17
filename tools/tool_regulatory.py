"""
title: Regulatory Lookup Tool
version: 1.0.0
description: Multi-region regulatory database lookup for EU, US, WHO standards and medical device regulations.
author: AI.STACK
author_url: https://github.com/Rinkatecam/aistack
requirements: pydantic, requests

# SYSTEM PROMPT FOR AI
# ====================
# Look up regulatory information from multiple sources.
#
# REGIONS (configurable via Valve):
#   EU  - EUR-Lex, MDR, IVDR
#   US  - FDA, CFR Title 21
#   WHO - WHO guidelines
#   ISO - ISO standards
#   PubMed - Scientific literature
#
# USE search_regulation(), lookup_standard(), check_classification()
"""

import os
import re
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class Tools:
    class Valves(BaseModel):
        default_region: str = Field(
            default="EU",
            description="Default regulatory region: EU, US, WHO, or ALL"
        )
        enabled_regions: str = Field(
            default="EU,US,WHO,ISO",
            description="Comma-separated list of enabled regions"
        )
        cache_results: bool = Field(
            default=True,
            description="Cache search results"
        )
        timeout_seconds: int = Field(
            default=15,
            description="API request timeout"
        )
        max_results: int = Field(
            default=10,
            description="Maximum results to return"
        )

    def __init__(self):
        self.citation = True
        self.valves = self.Valves()
        self._cache = {}

    def _get_enabled_regions(self) -> List[str]:
        return [r.strip().upper() for r in self.valves.enabled_regions.split(',')]

    def _make_request(self, url: str, headers: Dict = None) -> Optional[str]:
        """Make HTTP request."""
        try:
            req = urllib.request.Request(
                url,
                headers=headers or {
                    'User-Agent': 'Mozilla/5.0 (compatible; AI-Stack/1.0)',
                    'Accept': 'application/json, text/html'
                }
            )
            with urllib.request.urlopen(req, timeout=self.valves.timeout_seconds) as response:
                return response.read().decode('utf-8', errors='replace')
        except Exception as e:
            return None

    def search_eur_lex(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search EUR-Lex for EU regulations."""
        results = []
        try:
            encoded = urllib.parse.quote(query)
            # EUR-Lex SPARQL endpoint or search
            url = f"https://eur-lex.europa.eu/search.html?scope=EURLEX&text={encoded}&type=quick"

            # Note: EUR-Lex doesn't have a simple REST API
            # This provides the search URL for reference
            results.append({
                'title': f'EUR-Lex search for: {query}',
                'source': 'EUR-Lex',
                'url': url,
                'type': 'search_link',
                'description': 'Click link to view results on EUR-Lex portal'
            })

            # Add common MDR/IVDR references if related terms found
            mdr_keywords = ['medical device', 'mdr', 'device', 'ce mark', 'notified body']
            ivdr_keywords = ['ivd', 'diagnostic', 'ivdr', 'in vitro']

            if any(kw in query.lower() for kw in mdr_keywords):
                results.append({
                    'title': 'Regulation (EU) 2017/745 - Medical Device Regulation (MDR)',
                    'source': 'EUR-Lex',
                    'url': 'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32017R0745',
                    'type': 'regulation',
                    'celex': '32017R0745'
                })

            if any(kw in query.lower() for kw in ivdr_keywords):
                results.append({
                    'title': 'Regulation (EU) 2017/746 - In Vitro Diagnostic Regulation (IVDR)',
                    'source': 'EUR-Lex',
                    'url': 'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32017R0746',
                    'type': 'regulation',
                    'celex': '32017R0746'
                })

        except Exception as e:
            results.append({'error': str(e), 'source': 'EUR-Lex'})

        return results

    def search_fda(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search FDA databases."""
        results = []
        try:
            # FDA openFDA API
            encoded = urllib.parse.quote(query)

            # Device database search
            device_url = f"https://api.fda.gov/device/510k.json?search={encoded}&limit={max_results}"
            response = self._make_request(device_url)

            if response:
                data = json.loads(response)
                for item in data.get('results', [])[:max_results]:
                    results.append({
                        'title': item.get('device_name', 'Unknown Device'),
                        'source': 'FDA 510(k)',
                        'k_number': item.get('k_number', ''),
                        'applicant': item.get('applicant_100_name', ''),
                        'decision_date': item.get('decision_date', ''),
                        'url': f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID={item.get('k_number', '')}",
                        'type': '510k'
                    })

            # Also provide CFR Title 21 reference
            if 'device' in query.lower() or 'medical' in query.lower():
                results.append({
                    'title': 'FDA CFR Title 21 - Food and Drugs',
                    'source': 'FDA',
                    'url': 'https://www.ecfr.gov/current/title-21',
                    'type': 'regulation',
                    'description': 'Code of Federal Regulations for FDA-regulated products'
                })

        except Exception as e:
            results.append({'error': str(e), 'source': 'FDA'})

        return results

    def search_who(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search WHO guidance documents."""
        results = []
        try:
            # WHO IRIS (Institutional Repository for Information Sharing)
            encoded = urllib.parse.quote(query)
            url = f"https://apps.who.int/iris/discover?query={encoded}"

            results.append({
                'title': f'WHO IRIS search: {query}',
                'source': 'WHO',
                'url': url,
                'type': 'search_link',
                'description': 'WHO institutional repository for guidelines and publications'
            })

            # Common WHO references for medical devices
            if 'medical device' in query.lower() or 'regulation' in query.lower():
                results.append({
                    'title': 'WHO Medical Devices Overview',
                    'source': 'WHO',
                    'url': 'https://www.who.int/health-topics/medical-devices',
                    'type': 'guidance'
                })

        except Exception as e:
            results.append({'error': str(e), 'source': 'WHO'})

        return results

    def search_iso(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search ISO standards."""
        results = []
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://www.iso.org/search.html?q={encoded}"

            results.append({
                'title': f'ISO Standards search: {query}',
                'source': 'ISO',
                'url': url,
                'type': 'search_link'
            })

            # Common medical device standards
            common_standards = {
                'quality': ('ISO 13485', 'Medical devices — Quality management systems'),
                'risk': ('ISO 14971', 'Medical devices — Application of risk management'),
                'biocompatibility': ('ISO 10993', 'Biological evaluation of medical devices'),
                'usability': ('IEC 62366', 'Medical devices — Application of usability engineering'),
                'software': ('IEC 62304', 'Medical device software — Software life cycle processes'),
                'steril': ('ISO 11135', 'Sterilization of health-care products'),
                'electrical': ('IEC 60601', 'Medical electrical equipment'),
                'packaging': ('ISO 11607', 'Packaging for terminally sterilized medical devices'),
            }

            query_lower = query.lower()
            for keyword, (standard, title) in common_standards.items():
                if keyword in query_lower:
                    results.append({
                        'title': f'{standard}: {title}',
                        'source': 'ISO',
                        'standard': standard,
                        'url': f'https://www.iso.org/search.html?q={urllib.parse.quote(standard)}',
                        'type': 'standard'
                    })

        except Exception as e:
            results.append({'error': str(e), 'source': 'ISO'})

        return results

    def search_pubmed(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search PubMed for scientific literature."""
        results = []
        try:
            encoded = urllib.parse.quote(query)

            # PubMed E-utilities
            search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={encoded}&retmode=json&retmax={max_results}"

            response = self._make_request(search_url)
            if response:
                data = json.loads(response)
                ids = data.get('esearchresult', {}).get('idlist', [])

                if ids:
                    # Fetch summaries
                    ids_str = ','.join(ids)
                    summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={ids_str}&retmode=json"

                    summary_response = self._make_request(summary_url)
                    if summary_response:
                        summary_data = json.loads(summary_response)
                        articles = summary_data.get('result', {})

                        for pmid in ids:
                            if pmid in articles:
                                article = articles[pmid]
                                results.append({
                                    'title': article.get('title', 'Unknown'),
                                    'source': 'PubMed',
                                    'pmid': pmid,
                                    'authors': ', '.join([a.get('name', '') for a in article.get('authors', [])[:3]]),
                                    'journal': article.get('fulljournalname', ''),
                                    'year': article.get('pubdate', '')[:4],
                                    'url': f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/',
                                    'type': 'article'
                                })

        except Exception as e:
            results.append({'error': str(e), 'source': 'PubMed'})

        return results

    def search_regulation(self, query: str, region: str = "") -> str:
        """
        Search regulatory databases across configured regions.

        Args:
            query: Search terms (e.g., "medical device software", "biocompatibility")
            region: Specific region (EU, US, WHO, ISO) or empty for default

        Returns:
            Search results from regulatory databases.
        """
        if not region:
            region = self.valves.default_region

        regions = region.upper().split(',') if ',' in region else [region.upper()]

        if 'ALL' in regions:
            regions = self._get_enabled_regions()

        all_results = []

        for r in regions:
            if r == 'EU':
                all_results.extend(self.search_eur_lex(query))
            elif r == 'US':
                all_results.extend(self.search_fda(query))
            elif r == 'WHO':
                all_results.extend(self.search_who(query))
            elif r == 'ISO':
                all_results.extend(self.search_iso(query))
            elif r == 'PUBMED':
                all_results.extend(self.search_pubmed(query))

        # Format output
        result = [
            f"**Regulatory Search: '{query}'**",
            f"Regions: {', '.join(regions)}",
            "=" * 50,
            ""
        ]

        if not all_results:
            result.append("No results found.")
            return "\n".join(result)

        # Group by source
        by_source = {}
        for item in all_results:
            source = item.get('source', 'Unknown')
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(item)

        for source, items in by_source.items():
            result.append(f"**{source}:**")
            for item in items[:self.valves.max_results]:
                if 'error' in item:
                    result.append(f"  ⚠️ Error: {item['error']}")
                else:
                    result.append(f"  • {item.get('title', 'Untitled')}")
                    if item.get('url'):
                        result.append(f"    URL: {item['url']}")
                    if item.get('type') == '510k':
                        result.append(f"    K#: {item.get('k_number', 'N/A')}")
                    if item.get('pmid'):
                        result.append(f"    PMID: {item['pmid']} | {item.get('journal', '')} ({item.get('year', '')})")
            result.append("")

        return "\n".join(result)

    def lookup_standard(self, standard_id: str) -> str:
        """
        Look up a specific standard by ID.

        Args:
            standard_id: Standard identifier (e.g., "ISO 13485", "IEC 62304", "21 CFR 820")

        Returns:
            Information about the standard.
        """
        standard_upper = standard_id.upper().strip()

        # Known standards database
        standards_db = {
            'ISO 13485': {
                'title': 'Medical devices — Quality management systems — Requirements for regulatory purposes',
                'current_version': 'ISO 13485:2016',
                'description': 'Specifies requirements for a quality management system for medical devices.',
                'url': 'https://www.iso.org/standard/59752.html',
                'scope': 'All organizations involved in the life cycle of medical devices'
            },
            'ISO 14971': {
                'title': 'Medical devices — Application of risk management to medical devices',
                'current_version': 'ISO 14971:2019',
                'description': 'Framework for manufacturers to identify hazards, estimate and evaluate risks, control risks, and monitor effectiveness.',
                'url': 'https://www.iso.org/standard/72704.html',
                'scope': 'Risk management throughout the product lifecycle'
            },
            'IEC 62304': {
                'title': 'Medical device software — Software life cycle processes',
                'current_version': 'IEC 62304:2006/AMD1:2015',
                'description': 'Defines the life cycle requirements for medical device software development and maintenance.',
                'url': 'https://www.iec.ch/standards',
                'scope': 'Software as a medical device and software in medical devices'
            },
            'IEC 62366': {
                'title': 'Medical devices — Application of usability engineering to medical devices',
                'current_version': 'IEC 62366-1:2015',
                'description': 'Specifies a process for a manufacturer to analyze, specify, design, verify and validate usability.',
                'url': 'https://www.iec.ch/standards',
                'scope': 'User interface design and validation'
            },
            'ISO 10993': {
                'title': 'Biological evaluation of medical devices',
                'current_version': 'ISO 10993-1:2018',
                'description': 'Series of standards for evaluating biocompatibility of medical devices.',
                'url': 'https://www.iso.org/standard/68936.html',
                'scope': 'Biocompatibility testing and evaluation'
            },
            'IEC 60601': {
                'title': 'Medical electrical equipment',
                'current_version': 'IEC 60601-1:2005/AMD2:2020',
                'description': 'General requirements for basic safety and essential performance of medical electrical equipment.',
                'url': 'https://www.iec.ch/standards',
                'scope': 'Electrical safety for medical devices'
            },
            '21 CFR 820': {
                'title': 'Quality System Regulation (QSR)',
                'region': 'US (FDA)',
                'description': 'FDA regulations for quality system requirements for medical devices.',
                'url': 'https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-820',
                'scope': 'US medical device manufacturers'
            },
            'MDR 2017/745': {
                'title': 'Medical Device Regulation',
                'region': 'EU',
                'description': 'European regulation on medical devices, replacing MDD 93/42/EEC.',
                'url': 'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32017R0745',
                'scope': 'Medical devices placed on the EU market'
            },
            'IVDR 2017/746': {
                'title': 'In Vitro Diagnostic Regulation',
                'region': 'EU',
                'description': 'European regulation on in vitro diagnostic medical devices.',
                'url': 'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32017R0746',
                'scope': 'IVD devices placed on the EU market'
            }
        }

        # Try to find the standard
        found = None
        for key, value in standards_db.items():
            if key.upper().replace(' ', '') in standard_upper.replace(' ', ''):
                found = (key, value)
                break

        if found:
            key, info = found
            result = [
                f"**{key}**",
                "=" * 50,
                "",
                f"**Title:** {info.get('title', 'N/A')}",
                ""
            ]

            if info.get('current_version'):
                result.append(f"**Current Version:** {info['current_version']}")
            if info.get('region'):
                result.append(f"**Region:** {info['region']}")
            if info.get('description'):
                result.append(f"\n**Description:**\n{info['description']}")
            if info.get('scope'):
                result.append(f"\n**Scope:** {info['scope']}")
            if info.get('url'):
                result.append(f"\n**Reference:** {info['url']}")

            return "\n".join(result)
        else:
            return f"Standard '{standard_id}' not found in database.\n\nTry:\n  • ISO 13485, ISO 14971, ISO 10993\n  • IEC 62304, IEC 62366, IEC 60601\n  • 21 CFR 820, MDR 2017/745, IVDR 2017/746"

    def check_device_classification(self, device_type: str, region: str = "EU") -> str:
        """
        Get general device classification guidance.

        Args:
            device_type: Type of device (e.g., "surgical instrument", "software", "implant")
            region: Regulatory region (EU or US)

        Returns:
            Classification guidance.
        """
        region = region.upper()

        result = [
            f"**Device Classification Guidance**",
            f"Device Type: {device_type}",
            f"Region: {region}",
            "=" * 50,
            ""
        ]

        if region == "EU":
            result.extend([
                "**EU MDR Classification Rules:**",
                "",
                "Class I (lowest risk):",
                "  • Non-invasive devices",
                "  • Some surgical instruments (reusable)",
                "",
                "Class IIa (medium risk):",
                "  • Short-term invasive devices",
                "  • Active devices for diagnosis",
                "",
                "Class IIb (medium-high risk):",
                "  • Long-term implantable devices",
                "  • Active therapeutic devices",
                "",
                "Class III (highest risk):",
                "  • Long-term implantable devices (critical organs)",
                "  • Devices with medicinal substances",
                "  • Devices using non-viable animal tissues",
                "",
                "**Special Rules for Software (Rule 11):**",
                "  • Software driving a device: same class as device",
                "  • Standalone diagnostic software: Class IIa minimum",
                "  • Software for monitoring vital parameters: Class IIb/III",
                "",
                "Reference: MDR Annex VIII",
                "URL: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32017R0745",
            ])
        elif region == "US":
            result.extend([
                "**FDA Classification:**",
                "",
                "Class I (general controls):",
                "  • Low risk devices",
                "  • Most exempt from 510(k)",
                "",
                "Class II (special controls):",
                "  • Moderate risk devices",
                "  • Typically require 510(k) clearance",
                "",
                "Class III (premarket approval):",
                "  • High risk devices",
                "  • Require PMA approval",
                "",
                "**Software as Medical Device (SaMD):**",
                "  • FDA uses International Medical Device Regulators Forum (IMDRF) framework",
                "  • Classification based on healthcare situation and significance",
                "",
                "Reference: 21 CFR Parts 862-892",
                "URL: https://www.fda.gov/medical-devices/classify-your-medical-device",
            ])
        else:
            result.append(f"Classification guidance for region '{region}' not available.")
            result.append("Supported regions: EU, US")

        return "\n".join(result)

    def list_enabled_regions(self) -> str:
        """List enabled regulatory regions and their sources."""
        regions = self._get_enabled_regions()

        region_info = {
            'EU': ('European Union', ['EUR-Lex', 'MDR', 'IVDR', 'EU Harmonized Standards']),
            'US': ('United States', ['FDA openFDA', 'CFR Title 21', '510(k) Database']),
            'WHO': ('World Health Organization', ['WHO IRIS', 'WHO Guidelines']),
            'ISO': ('International Organization for Standardization', ['ISO Standards Catalog']),
            'PUBMED': ('Scientific Literature', ['PubMed/NCBI', 'Medical journals']),
        }

        result = [
            "**Enabled Regulatory Regions:**",
            "=" * 50,
            f"Default region: {self.valves.default_region}",
            ""
        ]

        for r in regions:
            info = region_info.get(r, (r, ['Unknown sources']))
            result.append(f"**{r}** - {info[0]}")
            for source in info[1]:
                result.append(f"  • {source}")
            result.append("")

        result.extend([
            "Usage:",
            '  search_regulation("medical device software", region="EU")',
            '  lookup_standard("ISO 13485")',
            '  check_device_classification("implant", region="US")',
        ])

        return "\n".join(result)
