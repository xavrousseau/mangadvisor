import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const src=readFileSync("apps/web/assets/appearance.js","utf8");
const {
  normalizeAppearance, DEFAULT_APPEARANCE, PRESETS, ACCENTS,
  loadAppearance, saveAppearance, applyAppearance,
} = await import("data:text/javascript;charset=utf-8,"+encodeURIComponent(src));

function storage(){
  const values=new Map();
  return {
    getItem:key=>values.get(key)??null,
    setItem:(key,value)=>values.set(key,value),
  };
}
test("approved night amber theme remains the default",()=>{
  assert.deepEqual(normalizeAppearance(null),DEFAULT_APPEARANCE);
  assert.deepEqual(normalizeAppearance({}),DEFAULT_APPEARANCE);
  assert.equal(loadAppearance(storage()).preset,"night");
  assert.equal(loadAppearance(storage()).accent,"amber");
});
test("the three designs and six accents are stable nonempty choices",()=>{
  assert.deepEqual(PRESETS.map(x=>x.id),["night","noir","paper"]);
  assert.equal(new Set(ACCENTS.map(x=>x.id)).size,6);
  assert.equal(ACCENTS.every(a=>/^#[0-9a-f]{6}$/i.test(a.hex)),true);
});
test("appearance is saved and restored on reload independently of user manga data",()=>{
  const store=storage();
  const selected={preset:"paper",accent:"mint",density:"compact"};
  assert.deepEqual(saveAppearance(store,selected),selected);
  assert.deepEqual(loadAppearance(store),selected);
});
test("unknown/corrupt inputs cannot inject CSS themes or colors",()=>{
  const bad={preset:'paper\" onclick=\"attack()',accent:"url(https://evil.test)",density:"hacker"};
  assert.deepEqual(normalizeAppearance(bad),DEFAULT_APPEARANCE);
  const store={getItem:()=>"{not JSON"};
  assert.deepEqual(loadAppearance(store),DEFAULT_APPEARANCE);
});
test("applying appearance changes only root DOM style and datasets",()=>{
  const element={dataset:{},style:{}};
  applyAppearance(element,{preset:"paper",accent:"ocean",density:"compact"});
  assert.deepEqual(element.dataset,{theme:"paper",accent:"ocean",density:"compact"});
  assert.equal(element.style.colorScheme,"light");
  applyAppearance(element,DEFAULT_APPEARANCE);
  assert.equal(element.style.colorScheme,"dark");
});
test("storage failure does not block a user's appearance change",()=>{
  const broken={getItem(){throw Error("blocked")},setItem(){throw Error("quota")}};
  assert.deepEqual(loadAppearance(broken),DEFAULT_APPEARANCE);
  assert.deepEqual(saveAppearance(broken,{preset:"noir",accent:"gold",density:"compact"}),{
    preset:"noir",accent:"gold",density:"compact",
  });
});
