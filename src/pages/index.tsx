import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import useBaseUrl from '@docusaurus/useBaseUrl';
import styles from './index.module.css';

const STEPS = [
  {num: 1, title: 'Registration', tools: 'ANTs', link: '/docs/workflow/registration'},
  {num: 2, title: 'Region warping', tools: 'ANTs · FSL', link: '/docs/workflow/warp-rois'},
  {num: 3, title: 'Corridor construction', tools: 'FSL', link: '/docs/workflow/corridor-mask'},
  {num: 4, title: 'Cutoff selection', tools: 'MRtrix3 · Python', link: '/docs/workflow/tune-cutoff'},
  {num: 5, title: 'Tractography', tools: 'MRtrix3', link: '/docs/workflow/tractography'},
  {num: 6, title: 'Bundle cleaning', tools: 'pyAFQ · DIPY', link: '/docs/workflow/cleaning'},
  {num: 7, title: 'Quality control', tools: 'Python · FSLeyes', link: '/docs/workflow/visual-qc'},
  {num: 8, title: 'Node profiles', tools: 'DIPY', link: '/docs/workflow/node-profiles'},
  {num: 9, title: 'Group-level inference', tools: 'R · Python', link: '/docs/workflow/nodewise-stats'},
];

function AtlasFigure() {
  return (<section className={styles.atlasSection}><div className="container">
    <div className={styles.atlasFigure}><div className="figure-panel">
      <img src={useBaseUrl('/img/fig_atlas_pathways.png')} alt="The seven bilateral pathways of the MesoConnect Atlas with their regions of interest" loading="lazy"/>
      <p className="figure-panel__caption">The seven bilateral pathways at the 50% threshold, in the three groupings used by the atlas authors. Figure from the MesoConnect repository (CC BY 4.0).</p>
    </div></div>
  </div></section>);
}

function Pipeline() {
  return (<section className={styles.pipelineSection}><div className="container">
    <Heading as="h2" className="text--center" style={{marginBottom: '0.5rem'}}>Workflow</Heading>
    <p className="text--center" style={{marginBottom: '2rem', color: 'var(--ifm-color-emphasis-600)'}}>
      Preprocessing is documented in the <a href="https://diffusiontensorimaging-repos.github.io/Diffusion-MRI-Preprocessing/docs/intro">Diffusion MRI Preprocessing tutorial</a>. The steps below begin from a T1-weighted image, a white-matter fibre orientation distribution and a brain mask.
    </p>
    <div className="pipeline-explorer pipeline-explorer--narrow">{STEPS.map((s) => (<div key={s.num}>
      <Link to={s.link} className="pipeline-explorer__stage">
        <div className="pipeline-explorer__number">{s.num}</div>
        <div className="pipeline-explorer__content"><p className="pipeline-explorer__title">{s.title}</p><p className="pipeline-explorer__tools">{s.tools}</p></div>
      </Link><div className="pipeline-explorer__arrow">&darr;</div></div>))}
      <Link to="pathname:///MesoConnect-Tutorial/explorer/" className="pipeline-explorer__stage">
        <div className="pipeline-explorer__number">&#9656;</div>
        <div className="pipeline-explorer__content"><p className="pipeline-explorer__title">Node-wise Tract Explorer</p><p className="pipeline-explorer__tools">Read the results file in the browser</p></div>
      </Link></div>
  </div></section>);
}

function Header() {
  const {siteConfig} = useDocusaurusContext();
  return (<header className={`hero hero--primary ${styles.heroBanner}`}><div className="container"><div className={styles.heroInner}>
    <p className={styles.heroLabel}>7 T mesolimbic connectivity atlas</p>
    <Heading as="h1" className="hero__title">{siteConfig.title}</Heading>
    <p className="hero__subtitle">{siteConfig.tagline}</p>
    <div className={styles.buttons}>
      <Link className="button button--secondary button--lg" to="/docs/">Start the tutorial</Link>
      <Link className="button button--outline button--lg" to="pathname:///MesoConnect-Tutorial/downloads/MesoConnect_Atlas.zip">Download the atlas (.zip)</Link>
    </div></div></div></header>);
}

export default function Home(): ReactNode {
  return (<Layout title="Home" description="Tutorial for the MesoConnect Atlas: participant-level tractography, bundle cleaning and along-tract microstructure for mesolimbic pathways.">
    <Header/><main>
      <AtlasFigure/>
      <Pipeline/></main></Layout>);
}
