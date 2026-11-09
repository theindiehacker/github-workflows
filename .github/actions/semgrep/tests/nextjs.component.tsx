// リクエストを受ける関数ではない普通のコンポーネントと関数は、引数を検出しない
export default function Button(props: { href: string; url: string }) {
  fetch(props.url);
  return <a href={props.href}>x</a>;
}

export async function loadCard({ url }: { url: string }) {
  return fetch(url);
}
