<script setup lang="ts">
import MediaBlock from '../components/MediaBlock.vue'
import MultipleChoice from '../components/MultipleChoice.vue'
import ShortAnswer from '../components/ShortAnswer.vue'
import TrueFalseNotGiven from '../components/TrueFalseNotGiven.vue'
import MatchingQuestion from '../components/MatchingQuestion.vue'
import OrderingQuestion from '../components/OrderingQuestion.vue'
import GraphBlock from '../components/GraphBlock.vue'
import NumericCode from '../components/NumericCode.vue'
</script>

<template>
  <div style="max-width: 720px; margin: 0 auto; padding: 24px; font-family: sans-serif;">
    <router-link to="/" style="display: inline-block; margin-bottom: 16px; cursor: pointer;">← Back to Landing</router-link>
    <h1>Test Object Templates — Demo</h1>

    <!-- ======== MEDIA BLOCK ======== -->
    <h2>1. Media Block</h2>
    <MediaBlock
      text="The chart below shows the number of visitors to three London museums between 2007 and 2012. Summarise the information by selecting and reporting the main features, and make comparisons where relevant."
      imageUrl="https://picsum.photos/seed/ielts/600/300"
    />

    <!-- ======== MULTIPLE CHOICE ======== -->
    <h2>2. Multiple Choice</h2>
    <MultipleChoice
      question="What does the speaker say about the new library?"
      :options="[
        'It will be open 24 hours.',
        'It will have a café inside.',
        'It will be located near the park.',
        'It will only be for students.',
      ]"
      :correctIndex="1"
    />

    <!-- ======== SHORT ANSWER ======== -->
    <h2>3. Short Answer</h2>
    <ShortAnswer
      question="What type of energy does the article say is the most promising for rural areas?"
      :acceptedAnswers="['solar', 'solar energy']"
    />

    <!-- ======== TRUE / FALSE / NOT GIVEN ======== -->
    <h2>4. True / False / Not Given</h2>
    <TrueFalseNotGiven
      statement="The museum was__(opened/founded)__ in the 19th century."
      correctAnswer="not-given"
    />

    <!-- ======== MATCHING ======== -->
    <h2>5. Matching</h2>
    <MatchingQuestion
      question="Match each researcher to the finding described in the passage."
      :prompts="['Dr. Smith', 'Prof. Lee', 'Dr. Patel']"
      :choices="['Discovered gene X', 'Published climate model', 'Developed new vaccine']"
      :correctMap="[2, 1, 0]"
    />

    <!-- ======== ORDERING ======== -->
    <h2>6. Ordering</h2>
    <OrderingQuestion
      question="Put the following events in the order they are mentioned in the recording."
      :items="['Arrival at airport', 'Hotel check-in', 'City tour', 'Museum visit']"
      :correctOrder="[0, 1, 3, 2]"
    />

    <!-- ======== GRAPH (MATH) ======== -->
    <h2>7. Graph (Math)</h2>
    <GraphBlock
      question="The graph of f(x) = x² − 3x + 1 is shown below. At which value of x does the function reach its minimum?"
      expression="x**2 - 3*x + 1"
      :xMin="-2"
      :xMax="5"
      :yMin="-3"
      :yMax="10"
    />
    <GraphBlock
      question="Sketch of y = sin(x)"
      expression="sin(x)"
      :xMin="-7"
      :xMax="7"
      :yMin="-1.5"
      :yMax="1.5"
      color="#e11d48"
    />

    <!-- ======== NUMERIC CODE (OTP-STYLE) ======== -->
    <h2>8. Numeric Code</h2>
    <NumericCode
      question="What is the 4-digit answer to: 12 × 3 + 7 × 8 = ?"
      :length="4"
      correctCode="0092"
    />
  </div>
</template>
