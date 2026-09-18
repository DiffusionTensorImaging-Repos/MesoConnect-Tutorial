import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'MesoConnect Atlas Tutorial',
  tagline: 'Participant-level tractography and along-tract microstructure with the MesoConnect mesolimbic atlas',
  favicon: 'img/favicon.ico',
  future: {v4: true},
  url: 'https://diffusiontensorimaging-repos.github.io',
  baseUrl: '/MesoConnect-Tutorial/',
  organizationName: 'DiffusionTensorImaging-Repos',
  projectName: 'MesoConnect-Tutorial',
  onBrokenLinks: 'warn',
  i18n: {defaultLocale: 'en', locales: ['en']},
  markdown: {mermaid: true, hooks: {onBrokenMarkdownLinks: 'warn'}},
  themes: ['@docusaurus/theme-mermaid'],
  presets: [
    ['classic', {
      docs: {sidebarPath: './sidebars.ts', editUrl: 'https://github.com/DiffusionTensorImaging-Repos/MesoConnect-Tutorial/tree/main/'},
      blog: false,
      theme: {customCss: './src/css/custom.css'},
    } satisfies Preset.Options],
  ],
  themeConfig: {
    colorMode: {defaultMode: 'light', respectPrefersColorScheme: true},
    navbar: {
      title: 'MesoConnect Atlas',
      logo: {alt: 'MesoConnect', src: 'img/logo.svg'},
      items: [
        {type: 'docSidebar', sidebarId: 'tutorialSidebar', position: 'left', label: 'Tutorial'},
        {to: '/docs/atlas/downloads', label: 'Downloads', position: 'left'},
        {href: 'pathname:///MesoConnect-Tutorial/explorer/', label: 'Explorer', position: 'left'},
        {href: 'https://diffusiontensorimaging-repos.github.io/TUBRIC-DTI/', label: 'Preprocessing (TUBRIC)', position: 'right'},
        {href: 'https://github.com/DiffusionTensorImaging-Repos/MesoConnect-Tutorial', label: 'GitHub', position: 'right'},
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {title: 'Tutorial', items: [
          {label: 'Introduction', to: '/docs/'},
          {label: 'Workflow', to: '/docs/workflow/overview'},
          {label: 'Parameters', to: '/docs/reference/parameters'},
          {label: 'Scripts', to: '/docs/reference/scripts'},
        ]},
        {title: 'Tools', items: [
          {label: 'MRtrix3', href: 'https://www.mrtrix.org/'},
          {label: 'ANTs', href: 'https://github.com/ANTsX/ANTs'},
          {label: 'FSL', href: 'https://fsl.fmrib.ox.ac.uk/fsl/fslwiki'},
          {label: 'pyAFQ', href: 'https://yeatmanlab.github.io/pyAFQ/'},
          {label: 'DIPY', href: 'https://dipy.org/'},
          {label: 'AMICO', href: 'https://github.com/daducci/AMICO'},
        ]},
        {title: 'Related', items: [
          {label: 'TUBRIC DTI preprocessing tutorial', href: 'https://diffusiontensorimaging-repos.github.io/TUBRIC-DTI/'},
          {label: 'Worked example repository (IMPACT)', href: 'https://github.com/DiffusionTensorImaging-Repos/SDN-IMPACT-DTI'},
          {label: 'Temple University', href: 'https://www.temple.edu'},
        ]},
      ],
      copyright: `Built with Docusaurus.`,
    },
    prism: {theme: prismThemes.github, darkTheme: prismThemes.dracula, additionalLanguages: ['bash', 'python', 'r']},
  } satisfies Preset.ThemeConfig,
};
export default config;
