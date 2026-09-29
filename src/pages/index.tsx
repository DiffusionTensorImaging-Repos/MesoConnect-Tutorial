import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import useBaseUrl from '@docusaurus/useBaseUrl';
import styles from './index.module.css';

const FACTS = [
  {value: '7', label: 'bilateral pathways'},
  {value: '7 T', label: 'Human Connectome Project diffusion MRI'},
  {value: '166–173', label: 'participants behind each map'},
  {value: '1 mm', label: 'FSL MNI152 grid'},
];

const STAGES = [
  {
    img: 'fig_regions_ortho.png',
    alt: 'Seed, target and atlas warped into one participant, shown in three planes',
    title: 'Registration and region warping',
    text: 'The pathway map and its seed and target regions move from standard space to the participant’s diffusion grid.',
  },
  {
    img: 'fig_inclusion_zone.png',
    alt: 'The dilated atlas with the seed and target, forming the corridor',
    title: 'Corridor construction',
    text: 'The warped map is dilated and joined to the endpoints, and the region outside it is excluded from tracking.',
  },
  {
    img: 'fig_cleaned_posterior.png',
    alt: 'A cleaned VTA to hippocampus bundle over the mean b = 0 image',
    title: 'Tractography and bundle cleaning',
    text: 'Streamlines are estimated from the participant’s own data, and outlying streamlines are removed.',
  },
  {
    img: 'fig_profile_ndi.png',
    alt: 'Neurite density sampled at 100 nodes along the bundle',
    title: 'Along-tract profiling',
    text: 'Each scalar map is sampled at 100 nodes, giving the values that enter the group-level models.',
  },
];

function Header() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={`hero hero--primary ${styles.heroBanner}`}>
      <div className="container">
        <div className={styles.heroInner}>
          <p className={styles.heroLabel}>7 T mesolimbic connectivity atlas</p>
          <Heading as="h1" className="hero__title">{siteConfig.title}</Heading>
          <p className="hero__subtitle">{siteConfig.tagline}</p>
          <div className={styles.buttons}>
            <Link className="button button--secondary button--lg" to="/docs/">Start the tutorial</Link>
            <Link
              className="button button--outline button--lg"
              to="pathname:///MesoConnect-Tutorial/downloads/MesoConnect_Atlas.zip">
              Download the atlas (.zip)
            </Link>
          </div>
        </div>
        <div className={styles.facts}>
          {FACTS.map((f) => (
            <div key={f.label} className={styles.fact}>
              <p className={styles.factValue}>{f.value}</p>
              <p className={styles.factLabel}>{f.label}</p>
            </div>
          ))}
        </div>
      </div>
    </header>
  );
}

function AtlasFigure() {
  return (
    <section className={styles.atlasSection}>
      <div className="container">
        <figure className={styles.atlasFigure}>
          <img
            src={useBaseUrl('/img/fig_atlas_pathways.png')}
            alt="The seven bilateral pathways of the MesoConnect Atlas with their regions of interest"
            loading="lazy"
          />
          <figcaption className={styles.atlasCaption}>
            The seven bilateral pathways at the 50% threshold, in the three groupings used by the
            atlas authors. Figure from the MesoConnect repository (CC BY 4.0).
          </figcaption>
        </figure>
        <p className={styles.atlasMore}>
          <Link to="/docs/atlas/construction">How the atlas was built &rarr;</Link>
        </p>
      </div>
    </section>
  );
}

function Method() {
  return (
    <section className={styles.methodSection}>
      <div className="container">
        <Heading as="h2" className="text--center" style={{marginBottom: '0.5rem'}}>
          Corridor-constrained tractography
        </Heading>
        <p
          className="text--center"
          style={{margin: '0 auto 2.5rem', maxWidth: '620px', color: 'var(--ifm-color-emphasis-600)'}}>
          The warped atlas confines tracking to one corridor. The streamlines are estimated from each
          participant&rsquo;s own diffusion data.
        </p>
        <div className={styles.stageGrid}>
          {STAGES.map((s) => (
            <div key={s.title} className={styles.stage}>
              <div className={styles.stageImage}>
                <img src={useBaseUrl(`/img/${s.img}`)} alt={s.alt} loading="lazy" />
              </div>
              <p className={styles.stageTitle}>{s.title}</p>
              <p className={styles.stageText}>{s.text}</p>
            </div>
          ))}
        </div>
        <p className={styles.methodFoot}>
          Diffusion data reach this workflow already corrected, from the{' '}
          <Link to="https://diffusiontensorimaging-repos.github.io/Diffusion-MRI-Preprocessing/docs/intro">
            Diffusion MRI Preprocessing tutorial
          </Link>{' '}
          or an equivalent pipeline.
        </p>
      </div>
    </section>
  );
}

export default function Home(): ReactNode {
  return (
    <Layout
      title="Home"
      description="Tutorial for the MesoConnect Atlas: participant-level tractography, bundle cleaning and along-tract microstructure for mesolimbic pathways.">
      <Header />
      <main>
        <AtlasFigure />
        <Method />
      </main>
    </Layout>
  );
}
