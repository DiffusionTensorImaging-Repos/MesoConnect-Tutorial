import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import styles from './index.module.css';

const STEPS = [
  {num: 1, title: 'Register MNI to T1', tools: 'ANTs', link: '/docs/workflow/registration'},
  {num: 2, title: 'Warp seed, target and atlas', tools: 'ANTs · FSL', link: '/docs/workflow/warp-rois'},
  {num: 3, title: 'Build the corridor', tools: 'FSL', link: '/docs/workflow/corridor-mask'},
  {num: 4, title: 'Tune the cutoff, and look', tools: 'MRtrix3 · Python', link: '/docs/workflow/tune-cutoff'},
  {num: 5, title: 'Tractography', tools: 'MRtrix3', link: '/docs/workflow/tractography'},
  {num: 6, title: 'Clean the bundles', tools: 'pyAFQ · DIPY', link: '/docs/workflow/cleaning'},
  {num: 7, title: 'Visual QC', tools: 'Python · FSLeyes', link: '/docs/workflow/visual-qc'},
  {num: 8, title: 'Node profiles', tools: 'DIPY', link: '/docs/workflow/node-profiles'},
  {num: 9, title: 'Node-wise statistics', tools: 'R', link: '/docs/workflow/nodewise-stats'},
];

const iconProps = {width: 48, height: 48, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor',
  strokeWidth: 1.5, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const};
const DatabaseIcon = () => (<svg {...iconProps} aria-hidden="true"><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.66 3.58 3 8 3s8-1.34 8-3V5"/><path d="M4 11v6c0 1.66 3.58 3 8 3s8-1.34 8-3v-6"/></svg>);
const StepsIcon = () => (<svg {...iconProps} aria-hidden="true"><path d="M3 21h4v-4"/><path d="M7 17h4v-4"/><path d="M11 13h4v-4"/><path d="M15 9h4V5"/><path d="M3 21h18"/></svg>);
const ChartIcon = () => (<svg {...iconProps} aria-hidden="true"><path d="M3 3v18h18"/><path d="M7 15l4-6 4 3 5-8"/></svg>);

type FeatureItem = {title: string; icon: ReactNode; description: ReactNode; link: string; linkText: string; external?: boolean};
const FEATURES: FeatureItem[] = [
  {title: 'Get the atlas', icon: <DatabaseIcon/>, description: <>Ten mesolimbic tract families in MNI 1 mm space, with the seed and target ROIs and where every one of them came from.</>, link: '/docs/atlas/overview', linkText: 'Atlas and downloads'},
  {title: 'Run the corridor workflow', icon: <StepsIcon/>, description: <>Nine steps from a warped atlas to cleaned subject-specific streamlines and 100-node profiles, with an audit and something to look at after each one.</>, link: '/docs/workflow/overview', linkText: 'Start the workflow'},
  {title: 'Explore your results', icon: <ChartIcon/>, description: <>Drop a node-wise results CSV into the browser and read the profiles, clusters and hemisphere comparison. Nothing is uploaded.</>, link: 'pathname:///MesoConnect-Tutorial/explorer/', linkText: 'Open the Explorer', external: true},
];

function Feature({title, icon, description, link, linkText, external}: FeatureItem) {
  return (
    <div className={clsx('col col--4')}><div className="feature-card">
      <div className="text--center" style={{marginBottom: '1rem', color: 'var(--ifm-color-primary)', display: 'flex', justifyContent: 'center'}}>{icon}</div>
      <div className="text--center padding-horiz--md">
        <Heading as="h3">{title}</Heading><p>{description}</p>
        <Link className="button button--primary button--sm" to={link}>{linkText}</Link>
      </div></div></div>);
}

function Pipeline() {
  return (<section className={styles.pipelineSection}><div className="container">
    <Heading as="h2" className="text--center" style={{marginBottom: '0.5rem'}}>The corridor workflow</Heading>
    <p className="text--center" style={{marginBottom: '2rem', color: 'var(--ifm-color-emphasis-600)'}}>
      Preprocessing is covered by the <a href="https://diffusiontensorimaging-repos.github.io/TUBRIC-DTI/">TUBRIC tutorial</a>. This site starts from a T1, a white-matter FOD and a brain mask.
    </p>
    <div className="pipeline-explorer">{STEPS.map((s, i) => (<div key={s.num}>
      <Link to={s.link} className="pipeline-explorer__stage">
        <div className="pipeline-explorer__number">{s.num}</div>
        <div className="pipeline-explorer__content"><p className="pipeline-explorer__title">{s.title}</p><p className="pipeline-explorer__tools">{s.tools}</p></div>
      </Link>{i < STEPS.length - 1 && <div className="pipeline-explorer__arrow">&darr;</div>}</div>))}</div>
  </div></section>);
}

function Header() {
  const {siteConfig} = useDocusaurusContext();
  return (<header className={clsx('hero hero--primary', styles.heroBanner)}><div className="container"><div className={styles.heroInner}>
    <p className={styles.heroLabel}>7 T mesolimbic connectivity atlas</p>
    <Heading as="h1" className="hero__title">{siteConfig.title}</Heading>
    <p className="hero__subtitle">{siteConfig.tagline}</p>
    <div className={styles.buttons}>
      <Link className="button button--secondary button--lg" to="/docs/">Start here</Link>
      <Link className="button button--outline button--lg" to="/docs/workflow/overview" style={{color: 'white', borderColor: 'rgba(255,255,255,0.5)', marginLeft: '1rem'}}>Workflow</Link>
    </div></div></div></header>);
}

export default function Home(): ReactNode {
  return (<Layout title="Home" description="Tutorial for the MesoConnect Atlas: corridor-guided tractography of mesolimbic pathways, cleaning, node-wise microstructure and statistics.">
    <Header/><main>
      <section className={styles.features}><div className="container"><div className="row" style={{gap: '1.5rem 0'}}>{FEATURES.map((p, i) => <Feature key={i} {...p}/>)}</div></div></section>
      <Pipeline/></main></Layout>);
}
