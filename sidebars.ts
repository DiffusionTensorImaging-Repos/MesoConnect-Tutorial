import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';
const sidebars: SidebarsConfig = {
  tutorialSidebar: [
    'intro',
    {type: 'category', label: 'Atlas', collapsed: false, items: ['atlas/overview', 'atlas/tracts', 'atlas/downloads']},
    {type: 'category', label: 'Workflow', collapsed: false, items: [
      'workflow/overview', 'workflow/registration', 'workflow/warp-rois', 'workflow/corridor-mask',
      'workflow/tune-cutoff', 'workflow/tractography', 'workflow/cleaning', 'workflow/visual-qc',
      'workflow/node-profiles', 'workflow/nodewise-stats']},
    'explorer',
    {type: 'category', label: 'Alternative approaches', items: ['appendix/whole-tract', 'appendix/synthetic-streamlines']},
    {type: 'category', label: 'Reference', items: ['reference/parameters', 'reference/troubleshooting', 'reference/software', 'reference/scripts', 'reference/methods-text', 'reference/abbreviations', 'reference/citation', 'reference/references']},
  ],
};
export default sidebars;
