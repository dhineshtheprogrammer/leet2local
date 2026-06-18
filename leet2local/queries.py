QUESTION_LIST = """
query questionList($filters: QuestionListFilterInput) {
  questionList(
    categorySlug: ""
    limit: 1
    skip: 0
    filters: $filters
  ) {
    questions {
      frontendQuestionId: questionFrontendId
      titleSlug
    }
  }
}
"""

QUESTION_DATA = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionId
    questionFrontendId
    title
    titleSlug
    content
    difficulty
    exampleTestcases
    codeSnippets {
      lang
      langSlug
      code
    }
    sampleTestCase
    metaData
  }
}
"""

# Submission uses LeetCode's REST API, not GraphQL.
# See submitter.py for the endpoints used.
