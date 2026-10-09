package com.demo;

import com.demo.TextUtil;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class TextUtil_isEmpty_Str_Test_Boundary_33 {


    @Test
    public void testIsEmptyWithNullString() {
        String s = null;

        boolean result = TextUtil.isEmpty(s);

        Assertions.assertTrue(result, "isEmpty(null) should return true because the null check short-circuits");
    }

}
