export default function Page(props: { searchParams: { u: string } }) {
  // ruleid: nextjs-ssrf
  fetch(props.searchParams.u);
  return null;
}
